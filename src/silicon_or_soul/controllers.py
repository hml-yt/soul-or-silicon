from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass

from serial import Serial, SerialException
from serial.tools.list_ports_common import ListPortInfo
from serial.tools import list_ports

from . import config
from .input import VoteAction


_log = logging.getLogger(__name__)

_PLAYER_IDS = {
    "PLAYER_1": 0,
    "PLAYER_2": 1,
    "PLAYER_3": 2,
}


@dataclass
class _ControllerConnection:
    device: str
    serial_handle: Serial
    player_index: int


class ControllerManager:
    def __init__(self) -> None:
        self._connections: dict[str, _ControllerConnection] = {}
        self._action_queue: queue.Queue[VoteAction] = queue.Queue()
        self._command_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._worker_loop, name="controller-io", daemon=True)
        if config.CONTROLLER_DEBUG:
            _log.debug("ControllerManager initialized (scan_interval=%.2fs)", config.CONTROLLER_SCAN_INTERVAL_SECONDS)
        self._worker.start()

    def poll(self, now: float) -> list[VoteAction]:
        # Compatibility wrapper; `now` is no longer used.
        return self.drain_actions()

    def drain_actions(self) -> list[VoteAction]:
        actions: list[VoteAction] = []
        while True:
            try:
                actions.append(self._action_queue.get_nowait())
            except queue.Empty:
                break
        if config.CONTROLLER_DEBUG and actions:
            _log.debug("drain_actions(): %d action(s): %s", len(actions), actions)
        return actions

    def send_all(self, command: str) -> None:
        if config.CONTROLLER_DEBUG:
            _log.debug("enqueue send_all(%r)", command)
        self._command_queue.put(command)

    def close(self) -> None:
        self._stop_event.set()
        self._worker.join(timeout=2.0)
        for device in list(self._connections.keys()):
            self._disconnect(device)

    def _worker_loop(self) -> None:
        # Schedule with absolute time to avoid immediate re-scan loops after
        # long handshakes.
        next_scan_at = 0.0
        while not self._stop_event.is_set():
            now = time.monotonic()
            if now >= next_scan_at:
                try:
                    self._scan_once()
                except Exception:
                    _log.exception("unexpected error during controller scan")
                next_scan_at = time.monotonic() + config.CONTROLLER_SCAN_INTERVAL_SECONDS

            try:
                self._process_outbound_commands()
                self._read_votes()
            except Exception:
                _log.exception("unexpected controller worker error")

            self._stop_event.wait(0.01)

        for device in list(self._connections.keys()):
            self._disconnect(device)

    def _scan_once(self) -> None:
        ports = list(list_ports.comports())
        available_devices = {port.device for port in ports}
        if config.CONTROLLER_DEBUG:
            _log.debug("scan: %d port(s) visible: %s", len(ports), sorted(available_devices))

        for device in list(self._connections.keys()):
            if device not in available_devices:
                self._disconnect(device)

        assigned_players = {conn.player_index for conn in self._connections.values()}
        candidate_ports = [port for port in ports if self._is_candidate_port(port)]
        if config.CONTROLLER_DEBUG:
            _log.debug("scan: %d candidate port(s): %s", len(candidate_ports), [p.device for p in candidate_ports])
        for port in candidate_ports:
            device = port.device
            if device in self._connections:
                continue
            if config.CONTROLLER_DEBUG:
                _log.debug("handshake start: %s (%s)", device, getattr(port, "description", ""))
            player_index = self._try_handshake(device)
            if player_index is None:
                if config.CONTROLLER_DEBUG:
                    _log.debug("handshake failed: %s", device)
                continue
            if player_index in assigned_players:
                # Duplicate board identity; keep the first active one.
                if config.CONTROLLER_DEBUG:
                    _log.debug("duplicate player id %d on %s; disconnecting duplicate", player_index, device)
                self._disconnect(device)
                continue
            assigned_players.add(player_index)
            if config.CONTROLLER_DEBUG:
                _log.debug("connected: %s -> player=%d", device, player_index)

    @staticmethod
    def _is_candidate_port(port: ListPortInfo) -> bool:
        device = (port.device or "").lower()
        desc = (getattr(port, "description", "") or "").lower()
        manufacturer = (getattr(port, "manufacturer", "") or "").lower()
        product = (getattr(port, "product", "") or "").lower()
        hwid = (getattr(port, "hwid", "") or "").lower()

        if not sys.platform.startswith("linux"):
            return True

        if device.startswith("/dev/ttyacm") or device.startswith("/dev/ttyusb"):
            return True

        fingerprint = " ".join((desc, manufacturer, product, hwid))
        usb_markers = ("arduino", "xiao", "rp2040", "usb", "cdc", "serial")
        return any(marker in fingerprint for marker in usb_markers)

    def _try_handshake(self, device: str) -> int | None:
        serial_handle: Serial | None = None
        try:
            serial_handle = Serial(
                device,
                baudrate=config.CONTROLLER_BAUDRATE,
                timeout=0,
                write_timeout=0,
            )
            # Many USB serial boards reset on port-open (DTR) and need a brief
            # grace period before they can respond to handshake commands.
            time.sleep(0.35)

            serial_handle.reset_input_buffer()
            serial_handle.reset_output_buffer()

            handshake_payload = f"{config.CONTROLLER_HANDSHAKE_COMMAND}\n".encode("utf-8")
            serial_handle.write(handshake_payload)
            serial_handle.flush()

            deadline = time.monotonic() + config.CONTROLLER_HANDSHAKE_TIMEOUT_SECONDS
            next_handshake_at = time.monotonic() + 0.35
            while time.monotonic() < deadline:
                line = self._readline(serial_handle)
                if config.CONTROLLER_DEBUG and line:
                    _log.debug("handshake rx <- %s: %r", device, line)
                if line in _PLAYER_IDS:
                    player_index = _PLAYER_IDS[line]
                    self._connections[device] = _ControllerConnection(
                        device=device,
                        serial_handle=serial_handle,
                        player_index=player_index,
                    )
                    # Immediately clear any stale vote/lock state on connect so a
                    # controller discovered mid-round can still participate.
                    try:
                        serial_handle.write(b"RESET\n")
                        serial_handle.flush()
                        if config.CONTROLLER_DEBUG:
                            _log.debug("sent %r -> %s (post-handshake)", "RESET", device)
                    except (SerialException, OSError):
                        self._disconnect(device)
                        return None
                    return player_index
                if line:
                    continue
                # Re-send handshake periodically in case the board was still
                # booting when we sent the first prompt.
                if time.monotonic() >= next_handshake_at:
                    try:
                        serial_handle.write(handshake_payload)
                        serial_handle.flush()
                        if config.CONTROLLER_DEBUG:
                            _log.debug("handshake retry -> %s", device)
                    except (SerialException, OSError):
                        self._disconnect(device)
                        return None
                    next_handshake_at = time.monotonic() + 0.35
                time.sleep(0.01)
        except (SerialException, OSError):
            return None

        if serial_handle is not None:
            try:
                serial_handle.close()
            except (SerialException, OSError):
                pass
        return None

    def _process_outbound_commands(self) -> None:
        pending: list[str] = []
        while True:
            try:
                pending.append(self._command_queue.get_nowait())
            except queue.Empty:
                break

        if not pending:
            return

        for command in pending:
            payload = f"{command}\n".encode("utf-8")
            if config.CONTROLLER_DEBUG:
                _log.debug("send_all(%r) -> %d connection(s)", command, len(self._connections))
            for device, conn in list(self._connections.items()):
                try:
                    conn.serial_handle.write(payload)
                    conn.serial_handle.flush()
                    if config.CONTROLLER_DEBUG:
                        _log.debug("sent %r -> %s (player=%d)", command, device, conn.player_index)
                except (SerialException, OSError):
                    if config.CONTROLLER_DEBUG:
                        _log.debug("send failed -> %s (player=%d), disconnecting", device, conn.player_index)
                    self._disconnect(device)

    def _read_votes(self) -> None:
        for device, conn in list(self._connections.items()):
            try:
                while True:
                    line = self._readline(conn.serial_handle)
                    if not line:
                        break
                    if config.CONTROLLER_DEBUG and config.CONTROLLER_DEBUG_RAW_LINES:
                        _log.debug("rx <- %s (player=%d): %r", device, conn.player_index, line)
                    if line == "VOTE:SILICON":
                        self._action_queue.put(VoteAction(player_index=conn.player_index, choice="Silicon"))
                    elif line == "VOTE:SOUL":
                        self._action_queue.put(VoteAction(player_index=conn.player_index, choice="Soul"))
                    elif config.CONTROLLER_DEBUG and line:
                        _log.debug("ignored line <- %s (player=%d): %r", device, conn.player_index, line)
            except (SerialException, OSError):
                self._disconnect(device)

    def _disconnect(self, device: str) -> None:
        conn = self._connections.pop(device, None)
        if conn is None:
            return
        if config.CONTROLLER_DEBUG:
            _log.debug("disconnect: %s (player=%d)", device, conn.player_index)
        try:
            conn.serial_handle.close()
        except (SerialException, OSError):
            pass

    @staticmethod
    def _readline(serial_handle: Serial) -> str:
        try:
            raw = serial_handle.readline()
        except (SerialException, OSError):
            return ""
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore").strip()

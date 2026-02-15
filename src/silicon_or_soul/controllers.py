from __future__ import annotations

import time
from dataclasses import dataclass

from serial import Serial, SerialException
from serial.tools import list_ports

from . import config
from .input import VoteAction


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
        self._last_scan_at = 0.0

    def poll(self, now: float) -> list[VoteAction]:
        self._rescan_if_needed(now)
        return self._read_votes()

    def send_all(self, command: str) -> None:
        payload = f"{command}\n".encode("utf-8")
        for device, conn in list(self._connections.items()):
            try:
                conn.serial_handle.write(payload)
                conn.serial_handle.flush()
            except (SerialException, OSError):
                self._disconnect(device)

    def close(self) -> None:
        for device in list(self._connections.keys()):
            self._disconnect(device)

    def _rescan_if_needed(self, now: float) -> None:
        if (now - self._last_scan_at) < config.CONTROLLER_SCAN_INTERVAL_SECONDS:
            return
        self._last_scan_at = now
        self._scan_once()

    def _scan_once(self) -> None:
        available_devices = {port.device for port in list_ports.comports()}

        for device in list(self._connections.keys()):
            if device not in available_devices:
                self._disconnect(device)

        assigned_players = {conn.player_index for conn in self._connections.values()}
        for port in list_ports.comports():
            device = port.device
            if device in self._connections:
                continue
            player_index = self._try_handshake(device)
            if player_index is None:
                continue
            if player_index in assigned_players:
                # Duplicate board identity; keep the first active one.
                self._disconnect(device)
                continue
            assigned_players.add(player_index)

    def _try_handshake(self, device: str) -> int | None:
        serial_handle: Serial | None = None
        try:
            serial_handle = Serial(
                device,
                baudrate=config.CONTROLLER_BAUDRATE,
                timeout=0,
                write_timeout=0,
            )
            serial_handle.reset_input_buffer()
            serial_handle.reset_output_buffer()
            serial_handle.write(f"{config.CONTROLLER_HANDSHAKE_COMMAND}\n".encode("utf-8"))
            serial_handle.flush()

            deadline = time.monotonic() + config.CONTROLLER_HANDSHAKE_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                line = self._readline(serial_handle)
                if line in _PLAYER_IDS:
                    player_index = _PLAYER_IDS[line]
                    self._connections[device] = _ControllerConnection(
                        device=device,
                        serial_handle=serial_handle,
                        player_index=player_index,
                    )
                    return player_index
                if line:
                    continue
                time.sleep(0.01)
        except (SerialException, OSError):
            return None

        if serial_handle is not None:
            try:
                serial_handle.close()
            except (SerialException, OSError):
                pass
        return None

    def _read_votes(self) -> list[VoteAction]:
        actions: list[VoteAction] = []
        for device, conn in list(self._connections.items()):
            try:
                while True:
                    line = self._readline(conn.serial_handle)
                    if not line:
                        break
                    if line == "VOTE:SILICON":
                        actions.append(VoteAction(player_index=conn.player_index, choice="Silicon"))
                    elif line == "VOTE:SOUL":
                        actions.append(VoteAction(player_index=conn.player_index, choice="Soul"))
            except (SerialException, OSError):
                self._disconnect(device)
        return actions

    def _disconnect(self, device: str) -> None:
        conn = self._connections.pop(device, None)
        if conn is None:
            return
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

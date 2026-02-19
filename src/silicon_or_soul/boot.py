from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import time
import tty
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from .controllers import ControllerManager


def _console_stream() -> TextIO:
    if sys.stdout.isatty():
        return sys.stdout
    return open("/dev/tty", "w", encoding="utf-8", errors="ignore")


def _draw_boot_screen() -> None:
    lines = (
        "",
        "SILICON OR SOUL",
        "",
        "Press any key to start",
        "Press ESC to quit",
        "",
    )
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    seq = "\x1b[2J\x1b[H\x1b[?25l"
    stream: TextIO | None = None
    try:
        stream = _console_stream()
        stream.write(seq)
        for line in lines:
            stream.write(f"{line.center(width)}\n")
        stream.flush()
    finally:
        if stream is not None and stream is not sys.stdout:
            stream.close()


def _open_tty_reader() -> tuple[int | None, TextIO | None]:
    if sys.stdin.isatty():
        return sys.stdin.fileno(), None
    try:
        reader = open("/dev/tty", "rb", buffering=0)
        return reader.fileno(), reader
    except OSError:
        return None, None


def wait_for_boot_start(
    controller_manager: "ControllerManager | None" = None,
    poll_seconds: float = 0.03,
) -> bool:
    """
    Show a console splash and block until keyboard/controller activity.

    Returns:
        True: continue startup.
        False: user chose to quit (ESC).
    """
    _draw_boot_screen()

    fd, reader = _open_tty_reader()
    old_attrs = None
    try:
        if fd is not None:
            old_attrs = termios.tcgetattr(fd)
            tty.setcbreak(fd)

        while True:
            if controller_manager is not None and controller_manager.drain_actions():
                return True

            if fd is None:
                time.sleep(poll_seconds)
                continue

            ready, _, _ = select.select([fd], [], [], poll_seconds)
            if not ready:
                continue
            key = os.read(fd, 1)
            if not key:
                continue
            if key == b"\x1b":
                return False
            return True
    finally:
        if fd is not None and old_attrs is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        if reader is not None:
            reader.close()

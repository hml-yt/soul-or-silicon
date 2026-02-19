from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config


def _blank_console() -> None:
    # Clear screen + home + hide cursor (helps avoid terminal leftovers on VT).
    seq = "\x1b[2J\x1b[H\x1b[?25l"
    try:
        if sys.stdout.isatty():
            sys.stdout.write(seq)
            sys.stdout.flush()
            return
    except Exception:
        pass
    try:
        with open("/dev/tty", "w", encoding="utf-8", errors="ignore") as tty:
            tty.write(seq)
            tty.flush()
    except Exception:
        pass


def restore_console_cursor() -> None:
    seq = "\x1b[?25h"
    try:
        if sys.stdout.isatty():
            sys.stdout.write(seq)
            sys.stdout.flush()
            return
    except Exception:
        pass
    try:
        with open("/dev/tty", "w", encoding="utf-8", errors="ignore") as tty:
            tty.write(seq)
            tty.flush()
    except Exception:
        pass


def play_intro_video(video_path: Path | None = None) -> bool:
    """
    Play intro video fullscreen using ffplay (SDL).

    This intentionally avoids Python video/audio decoding and just delegates to
    ffplay, which uses SDL for video output and handles A/V sync internally.
    """
    path = video_path if video_path is not None else (config.ROOT_DIR / "video" / "intro-1440p.mp4")
    if not path.exists():
        return False

    ffplay = shutil.which("ffplay")
    if not ffplay:
        logging.getLogger(__name__).warning("ffplay not found; skipping intro")
        return False

    # SDL console mode hint: if not under a desktop session, prefer kmsdrm/fbcon.
    env = os.environ.copy()
    under_desktop = bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    if not under_desktop and not env.get("SDL_VIDEODRIVER"):
        if Path("/dev/dri/card0").exists():
            env["SDL_VIDEODRIVER"] = "kmsdrm"
        elif Path("/dev/fb0").exists():
            env["SDL_VIDEODRIVER"] = "fbcon"
    if not under_desktop and not env.get("SDL_AUDIODRIVER"):
        # Kiosk/service sessions usually do not run PulseAudio/PipeWire user
        # daemons; prefer direct ALSA output for reliable intro sound.
        env["SDL_AUDIODRIVER"] = "alsa"

    cmd = [
        ffplay,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostats",
        "-af",
        "volume=1.5",
        "-autoexit",
        "-fs",
        str(path),
    ]
    try:
        _blank_console()
        completed = subprocess.run(
            cmd,
            env=env,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return completed.returncode == 0
    except Exception:
        logging.getLogger(__name__).exception("ffplay intro playback failed")
        return False

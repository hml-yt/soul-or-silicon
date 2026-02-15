from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time

def _setup_sdl_env_for_console() -> None:
    """
    On Raspberry Pi OS Lite / console-only boots, SDL can pick a driver path that
    expects EGL/GL. Prefer framebuffer console when present, and default to
    software rendering.

    IMPORTANT: env vars must be set before the first SDL video init.
    """

    under_desktop = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if under_desktop:
        return

    # If the user already chose a driver, respect it.
    if os.environ.get("SDL_VIDEODRIVER"):
        os.environ.setdefault("SDL_RENDER_DRIVER", "software")
        return

    # Avoid EGL/GL renderer selection; keep it 2D/software. We intentionally
    # don't force a particular SDL video driver here because some distro SDL
    # builds omit `fbcon`. Driver selection/fallback happens in `_create_screen`.
    os.environ.setdefault("SDL_RENDER_DRIVER", "software")


_setup_sdl_env_for_console()

import pygame

from . import config
from .audio import AudioManager
try:
    from .controllers import ControllerManager
except Exception as e:  # pragma: no cover - optional hardware dependency
    ControllerManager = None  # type: ignore[assignment]
    _CONTROLLER_IMPORT_ERROR = True
    _CONTROLLER_IMPORT_ERROR_MESSAGE = f"{type(e).__name__}: {e}"
else:
    _CONTROLLER_IMPORT_ERROR = False
    _CONTROLLER_IMPORT_ERROR_MESSAGE = ""
from .game import Game
from .input import HostAction, InputManager, VoteAction
from .logging_jsonl import RoundLogger
from .songs import SongLibrary
from .ui import UI


def _setup_logging() -> None:
    # Keep logging quiet by default; only enable verbose controller logs when asked.
    if not config.CONTROLLER_DEBUG:
        return
    # Force a predictable console logger so DEBUG output always shows up, even if
    # another library configured logging earlier.
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def _create_screen() -> pygame.Surface:
    """
    Create the main display surface with pragmatic fallbacks.

    Some Linux/Wayland setups can throw `pygame.error: EGL not initialized` when
    requesting `FULLSCREEN | SCALED`. We progressively degrade flags/sizing, and
    as a last resort retry with the X11 video driver when available.
    """

    def try_modes() -> pygame.Surface | None:
        attempts: list[tuple[tuple[int, int], int]] = [
            (config.WINDOW_SIZE, pygame.FULLSCREEN | pygame.SCALED),
            (config.WINDOW_SIZE, pygame.FULLSCREEN),
            ((0, 0), pygame.FULLSCREEN),  # desktop resolution fullscreen
            (config.WINDOW_SIZE, pygame.SCALED),
            (config.WINDOW_SIZE, 0),
        ]
        last_error: pygame.error | None = None
        for size, flags in attempts:
            try:
                return pygame.display.set_mode(size, flags)
            except pygame.error as e:
                last_error = e
        if last_error is not None:
            raise last_error
        return None

    try:
        return try_modes()  # type: ignore[return-value]
    except pygame.error:
        # Linux console environments (e.g. Raspberry Pi OS Lite) may need an
        # explicit SDL video driver choice, and some SDL builds omit drivers like
        # `fbcon`. If we're not under X11/Wayland, try pragmatic fallbacks.
        if not sys.platform.startswith("linux"):
            raise
        under_desktop = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if under_desktop:
            raise

        candidates: list[str] = []
        # Prefer KMS/DRM (most common on modern Pi images), then fbcon if present.
        if Path("/dev/dri/card0").exists():
            candidates.append("kmsdrm")
        if Path("/dev/fb0").exists():
            candidates.append("fbcon")
        # Other optional backends.
        candidates.extend(["directfb", "svgalib"])

        current_driver = os.environ.get("SDL_VIDEODRIVER", "").lower()
        last_error: pygame.error | None = None
        for drv in candidates:
            if current_driver == drv:
                continue
            try:
                pygame.quit()
                os.environ["SDL_VIDEODRIVER"] = drv
                if drv == "fbcon":
                    os.environ.setdefault("SDL_FBDEV", "/dev/fb0")
                elif drv == "kmsdrm":
                    os.environ.setdefault("SDL_KMSDRM_DEVICE", "/dev/dri/card0")
                os.environ.setdefault("SDL_RENDER_DRIVER", "software")
                pygame.init()
                return try_modes()  # type: ignore[return-value]
            except pygame.error as e:
                last_error = e
                continue

        if last_error is not None:
            raise last_error
        raise


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="silicon-or-soul")
    parser.add_argument(
        "--player-name",
        action="append",
        default=[],
        help="Repeatable. Example: --player-name Alice --player-name Bob",
    )
    parser.add_argument(
        "--player-names",
        default="",
        help='Comma-separated. Example: --player-names "Alice,Bob,Carol"',
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args(sys.argv[1:])
    _setup_logging()
    if config.CONTROLLER_DEBUG:
        logging.getLogger(__name__).debug(
            "debug logging enabled (controllers_enabled=%s, controllers_import_ok=%s)",
            config.CONTROLLERS_ENABLED,
            not _CONTROLLER_IMPORT_ERROR,
        )
        if _CONTROLLER_IMPORT_ERROR:
            logging.getLogger(__name__).debug("controllers import error: %s", _CONTROLLER_IMPORT_ERROR_MESSAGE)

    # Note: `_create_screen()` may need to pick/initialize an SDL video driver on
    # console-only Linux systems, so we do it before initializing everything.
    screen = _create_screen()
    pygame.init()
    pygame.display.set_caption("Silicon Or Soul")
    clock = pygame.time.Clock()

    audio = AudioManager()
    library = SongLibrary()
    library.scan()
    logger = RoundLogger()
    game = Game(audio=audio, library=library, logger=logger)
    player_names: list[str] = []
    if args.player_name:
        player_names.extend(args.player_name)
    if args.player_names:
        player_names.extend([p.strip() for p in args.player_names.split(",")])
    if player_names:
        game.set_player_names(player_names)
    ui = UI(screen)
    input_manager = InputManager()
    controller_manager = None
    if config.CONTROLLERS_ENABLED and ControllerManager is not None:
        try:
            controller_manager = ControllerManager()
        except Exception:
            if config.CONTROLLER_DEBUG:
                logging.getLogger(__name__).exception("failed to initialize ControllerManager")
            controller_manager = None
    elif config.CONTROLLER_DEBUG and config.CONTROLLERS_ENABLED and ControllerManager is None:
        logging.getLogger(__name__).warning(
            "controllers enabled but ControllerManager is unavailable (is pyserial installed?)"
        )

    now = time.perf_counter()
    if not library.has_songs():
        game.state = "ERROR"
        game.error_message = "No songs found. Add files to songs/ai and songs/human."
    else:
        game.start_round(now)

    running = True
    previous_state = game.state
    while running:
        now = time.perf_counter()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    continue
                action = input_manager.handle_key(event.key)
                if isinstance(action, VoteAction):
                    game.register_vote(action.player_index, action.choice, now)
                elif isinstance(action, HostAction):
                    if action.action == "quit":
                        running = False
                    elif action.action == "pause":
                        game.toggle_pause(now)
                    elif action.action == "skip":
                        game.skip_round(now)

        if controller_manager is not None:
            for action in controller_manager.drain_actions():
                game.register_vote(action.player_index, action.choice, now)

        game.update(now)
        if controller_manager is not None and game.state != previous_state:
            if game.state == "VOTING":
                controller_manager.send_all("RESET")
            elif game.state == "REVEAL" and game.current_song is not None:
                if game.current_song.category == "Silicon":
                    controller_manager.send_all("WIN_SILICON")
                else:
                    controller_manager.send_all("WIN_SOUL")
        previous_state = game.state
        ui.draw(game, now)
        clock.tick(config.FPS)

    audio.stop_music()
    if controller_manager is not None:
        controller_manager.close()
    pygame.quit()


if __name__ == "__main__":
    main()


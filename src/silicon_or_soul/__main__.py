from __future__ import annotations

import time

import pygame

from . import config
from .audio import AudioManager
from .game import Game
from .input import HostAction, InputManager, VoteAction
from .logging_jsonl import RoundLogger
from .songs import SongLibrary
from .ui import UI


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(config.WINDOW_SIZE)
    pygame.display.set_caption("Silicon Or Soul")
    clock = pygame.time.Clock()

    audio = AudioManager()
    library = SongLibrary()
    library.scan()
    logger = RoundLogger()
    game = Game(audio=audio, library=library, logger=logger)
    ui = UI(screen)
    input_manager = InputManager()

    now = time.perf_counter()
    if not library.has_songs():
        game.state = "ERROR"
        game.error_message = "No songs found. Add files to songs/ai and songs/human."
    else:
        game.start_round(now)

    running = True
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

        game.update(now)
        ui.draw(game, now)
        clock.tick(config.FPS)

    audio.stop_music()
    pygame.quit()


if __name__ == "__main__":
    main()


from __future__ import annotations

from pathlib import Path

import pygame

ROOT_DIR = Path(__file__).resolve().parents[2]

SONGS_AI_DIR = ROOT_DIR / "songs" / "ai"
SONGS_HUMAN_DIR = ROOT_DIR / "songs" / "human"
SOUNDS_DIR = ROOT_DIR / "sounds"
LOGS_DIR = ROOT_DIR / "logs"

WINDOW_SIZE = (800, 480)
FPS = 60

VOTING_TIMEOUT_SECONDS = 15.0
REVEAL_DURATION_SECONDS = 4.0
INTERMISSION_SECONDS = 2.0

SCORE_ANIM_DURATION = 0.8
WINNER_HIGHLIGHT_DURATION = 2.5

MUSIC_VOLUME = 0.75
SFX_VOLUME = 0.9

RECENT_TRACK_MEMORY = 3

PLAYER_CONFIG = [
    {"name": "Player 1", "keys": {"silicon": pygame.K_a, "soul": pygame.K_s}},
    {"name": "Player 2", "keys": {"silicon": pygame.K_d, "soul": pygame.K_f}},
    {"name": "Player 3", "keys": {"silicon": pygame.K_g, "soul": pygame.K_h}},
]

HOST_KEYS = {
    "pause": pygame.K_p,
    "skip": pygame.K_n,
    "quit": pygame.K_q,
}

SOUND_FILES = {
    "start": "start.wav",
    "lock_in": "lock_in.wav",
    "reveal": "reveal.wav",
    "win": "win.wav",
    "lose": "lose.wav",
}

COLORS = {
    "background": (24, 24, 24),
    "text": (235, 235, 235),
    "muted": (140, 140, 140),
    "silicon": (0, 200, 255),
    "soul": (255, 140, 0),
    "winner": (120, 255, 120),
    "warning": (255, 80, 80),
    "panel": (40, 40, 40),
}


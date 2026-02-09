from __future__ import annotations

from pathlib import Path

import pygame

ROOT_DIR = Path(__file__).resolve().parents[2]

SONGS_AI_DIR = ROOT_DIR / "songs" / "ai"
SONGS_HUMAN_DIR = ROOT_DIR / "songs" / "human"
SOUNDS_DIR = ROOT_DIR / "sounds"
LOGS_DIR = ROOT_DIR / "logs"
ASSETS_DIR = ROOT_DIR / "assets"

# Resolution: 1920x1080 (HD) - pygame.SCALED handles 4K
WINDOW_SIZE = (1920, 1080)
FPS = 60

# Game Timing
CHOOSING_DURATION_SECONDS = 3.0
VOTING_TIMEOUT_SECONDS = 15.0
PRE_REVEAL_DURATION_SECONDS = 2.0
REVEAL_DURATION_SECONDS = 5.0
INTERMISSION_SECONDS = 2.0

# Animation Timing
SCORE_ANIM_DURATION = 0.8
WINNER_HIGHLIGHT_DURATION = 2.5
ROULETTE_TICK_INTERVAL_START = 0.05
ROULETTE_TICK_INTERVAL_END = 0.4

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
    # Optional extra sounds
    "tick": "tick.wav",
    "drumroll": "drumroll.wav",
}

COLORS = {
    # Cyberpunk Neon Palette
    "background_top": (10, 10, 25),      # Deep Blue/Purple
    "background_bottom": (0, 0, 10),     # Almost Black
    "text": (240, 240, 255),             # Bright White-Blue
    "muted": (100, 100, 140),            # Muted Blue-Grey
    
    # Neon Accents
    "silicon": (0, 255, 255),            # Cyan / Neon Blue
    "soul": (255, 100, 0),               # Neon Orange
    "winner": (50, 255, 50),             # Bright Neon Green
    "warning": (255, 50, 80),            # Neon Red
    
    # UI Elements
    "panel_bg": (20, 30, 40),            # Dark Blue-Grey (for glass effect base)
    "panel_border": (80, 100, 120),      # Light Blue-Grey
    "panel_glow": (0, 150, 255),         # Blue Glow
}

FONTS = {
    "primary": "Arial Rounded MT Bold",
    "secondary": "Helvetica",
    "fallback": "Arial",
}

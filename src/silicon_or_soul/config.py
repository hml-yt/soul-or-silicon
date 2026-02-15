from __future__ import annotations

from pathlib import Path

import pygame

ROOT_DIR = Path(__file__).resolve().parents[2]

SONGS_AI_DIR = ROOT_DIR / "songs" / "ai"
SONGS_HUMAN_DIR = ROOT_DIR / "songs" / "human"
SOUNDS_DIR = ROOT_DIR / "sounds"
LOGS_DIR = ROOT_DIR / "logs"
ASSETS_DIR = ROOT_DIR / "assets"

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
WINDOW_SIZE = (1920, 1080)
FPS = 60

# ---------------------------------------------------------------------------
# Game Timing
# ---------------------------------------------------------------------------
CHOOSING_DURATION_SECONDS = 3.5
VOTING_TIMEOUT_SECONDS = 50.0
PRE_REVEAL_DURATION_SECONDS = 2.5
REVEAL_DURATION_SECONDS = 5.0
INTERMISSION_SECONDS = 2.0
TOTAL_ROUNDS = 6

# ---------------------------------------------------------------------------
# Animation Timing
# ---------------------------------------------------------------------------
SCORE_ANIM_DURATION = 0.8
WINNER_HIGHLIGHT_DURATION = 4.0
ROULETTE_TICK_INTERVAL_START = 0.04
ROULETTE_TICK_INTERVAL_END = 0.35

# ---------------------------------------------------------------------------
# Champion Pedestal Animation
# ---------------------------------------------------------------------------
PEDESTAL_BLACKOUT_END = 1.2
PEDESTAL_RISE_END = 3.0
PEDESTAL_SCORE_END = 5.0
PEDESTAL_CROWN_END = 6.5
PEDESTAL_HEIGHTS = (350, 250, 200)   # 1st, 2nd, 3rd (pixels)
PEDESTAL_WIDTHS = (340, 300, 300)    # 1st, 2nd, 3rd (pixels)
PEDESTAL_GAP = 80                    # gap between podiums

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
SPEED_POINTS_MIN = 1
SPEED_POINTS_MAX = 3
SPEED_POINTS_EXP = 0.5
WRONG_ANSWER_PENALTY = 1

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
MUSIC_VOLUME = 0.75
SFX_VOLUME = 0.9

MUSIC_RANDOM_START = True
MUSIC_SNIPPET_SECONDS = VOTING_TIMEOUT_SECONDS

RECENT_TRACK_MEMORY = 3

# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------
PLAYER_CONFIG = [
    {"name": "Player 1", "keys": {"silicon": pygame.K_a, "soul": pygame.K_s}},
    {"name": "Player 2", "keys": {"silicon": pygame.K_d, "soul": pygame.K_f}},
    {"name": "Player 3", "keys": {"silicon": pygame.K_g, "soul": pygame.K_h}},
]

HOST_KEYS = {
    "pause": (pygame.K_p, pygame.K_b),
    "skip": (pygame.K_n, pygame.K_RIGHT),
    "quit": pygame.K_q,
}

# ---------------------------------------------------------------------------
# External Controllers (Arduino over USB serial)
# ---------------------------------------------------------------------------
CONTROLLERS_ENABLED = True
CONTROLLER_BAUDRATE = 9600
CONTROLLER_SCAN_INTERVAL_SECONDS = 1.5
CONTROLLER_HANDSHAKE_TIMEOUT_SECONDS = 0.75
CONTROLLER_HANDSHAKE_COMMAND = "WHO_ARE_YOU?"

# Debug logging for controller discovery/handshake/votes.
# Turn on when diagnosing USB serial issues.
CONTROLLER_DEBUG = False
# Log every raw line received from controllers (can be noisy).
CONTROLLER_DEBUG_RAW_LINES = False

SOUND_FILES = {
    "start": "start.wav",
    "lock_in": "lock_in.wav",
    "reveal": "reveal.wav",
    "win": "win.wav",
    "lose": "lose.wav",
    "tick": "tick.wav",
    "drumroll": "drumroll.wav",
    "triumph": "triumph.wav",
}

# ---------------------------------------------------------------------------
# Color Palette – Cyberpunk Neon
# ---------------------------------------------------------------------------
COLORS = {
    # Background gradient
    "bg_top": (8, 8, 30),
    "bg_bottom": (2, 2, 12),

    # Text
    "text": (240, 240, 255),
    "muted": (90, 90, 130),

    # Neon Accents
    "silicon": (0, 220, 255),
    "silicon_dim": (0, 80, 100),
    "soul": (255, 100, 0),
    "soul_dim": (100, 40, 0),
    "winner": (50, 255, 80),
    "loser": (255, 50, 80),
    "warning": (255, 50, 80),

    # UI panels
    "panel_bg": (15, 20, 35),
    "panel_border": (50, 70, 100),
    "panel_glow": (0, 120, 255),

    # Misc
    "gold": (255, 215, 0),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}

# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------
PARTICLE_MAX = 300
BG_STAR_COUNT = 80
CONFETTI_BURST_COUNT = 120
CONFETTI_COLORS = [
    (255, 50, 80),
    (0, 220, 255),
    (255, 215, 0),
    (50, 255, 80),
    (255, 100, 0),
    (180, 80, 255),
]

# ---------------------------------------------------------------------------
# Fonts (tried in order, first match wins)
# ---------------------------------------------------------------------------
FONT_NAMES = ["Arial Rounded MT Bold", "Helvetica Neue", "Helvetica", "Arial"]

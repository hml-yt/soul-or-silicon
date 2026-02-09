from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import config


@dataclass(frozen=True)
class Song:
    path: Path
    category: str  # "Silicon" or "Soul"


class SongLibrary:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.songs_ai: list[Path] = []
        self.songs_human: list[Path] = []
        self.recent: deque[Path] = deque(maxlen=config.RECENT_TRACK_MEMORY)

    def scan(self) -> None:
        self.songs_ai = self._scan_dir(config.SONGS_AI_DIR)
        self.songs_human = self._scan_dir(config.SONGS_HUMAN_DIR)

    def has_songs(self) -> bool:
        return bool(self.songs_ai or self.songs_human)

    def pick(self, exclude: Iterable[Path] | None = None) -> Song | None:
        exclude_set = set(exclude or [])
        candidates = {
            "Silicon": [p for p in self.songs_ai if p not in exclude_set],
            "Soul": [p for p in self.songs_human if p not in exclude_set],
        }
        candidates = {k: v for k, v in candidates.items() if v}
        if not candidates:
            return None

        category = self.rng.choice(list(candidates.keys()))
        song = self._pick_from_list(candidates[category])
        if song is None:
            return None
        self.recent.append(song)
        return Song(path=song, category=category)

    def _pick_from_list(self, songs: list[Path]) -> Path | None:
        if not songs:
            return None
        non_recent = [p for p in songs if p not in self.recent]
        pick_from = non_recent or songs
        return self.rng.choice(pick_from)

    @staticmethod
    def _scan_dir(path: Path) -> list[Path]:
        if not path.exists():
            return []
        allowed = {".mp3", ".wav", ".ogg"}
        return sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() in allowed])


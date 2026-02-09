from __future__ import annotations

from pathlib import Path
import random

import pygame

from . import config


class AudioManager:
    def __init__(self) -> None:
        self.enabled = self._init_mixer()
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.rng = random.Random()
        if self.enabled:
            self._load_sfx()

    def _init_mixer(self) -> bool:
        try:
            pygame.mixer.init()
        except pygame.error:
            return False
        return True

    def _load_sfx(self) -> None:
        for name, filename in config.SOUND_FILES.items():
            sound_path = config.SOUNDS_DIR / filename
            if not sound_path.exists():
                continue
            try:
                sound = pygame.mixer.Sound(str(sound_path))
                sound.set_volume(config.SFX_VOLUME)
                self.sounds[name] = sound
            except pygame.error:
                continue

    def play_sfx(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def play_music(self, path: Path) -> bool:
        if not self.enabled:
            return False
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(config.MUSIC_VOLUME)
            start_pos = 0.0
            if config.MUSIC_RANDOM_START:
                start_pos = self._pick_music_start(path)
            try:
                pygame.mixer.music.play(start=start_pos)
            except pygame.error:
                pygame.mixer.music.play()
        except pygame.error:
            return False
        return True

    def stop_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.stop()

    def pause_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.pause()

    def resume_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.unpause()

    def _pick_music_start(self, path: Path) -> float:
        try:
            length = pygame.mixer.Sound(str(path)).get_length()
        except pygame.error:
            return 0.0

        snippet = max(0.0, config.MUSIC_SNIPPET_SECONDS)
        if length <= snippet:
            return 0.0
        return self.rng.uniform(0.0, max(0.0, length - snippet))


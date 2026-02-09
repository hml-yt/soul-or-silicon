from __future__ import annotations

from pathlib import Path

import pygame

from . import config


class AudioManager:
    def __init__(self) -> None:
        self.enabled = self._init_mixer()
        self.sounds: dict[str, pygame.mixer.Sound] = {}
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


from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class VoteAction:
    player_index: int
    choice: str


@dataclass(frozen=True)
class HostAction:
    action: str


class InputManager:
    def __init__(self) -> None:
        self.player_keys = []
        for player in config.PLAYER_CONFIG:
            self.player_keys.append(player["keys"])

    def handle_key(self, key: int) -> VoteAction | HostAction | None:
        for idx, keys in enumerate(self.player_keys):
            if key == keys["silicon"]:
                return VoteAction(player_index=idx, choice="Silicon")
            if key == keys["soul"]:
                return VoteAction(player_index=idx, choice="Soul")

        for action, host_key in config.HOST_KEYS.items():
            if isinstance(host_key, int) and key == host_key:
                return HostAction(action=action)
            if not isinstance(host_key, int) and key in host_key:
                return HostAction(action=action)
        return None


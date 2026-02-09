from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import config
from .audio import AudioManager
from .logging_jsonl import RoundLogger
from .songs import Song, SongLibrary


@dataclass
class Player:
    name: str
    score: int = 0
    vote: str | None = None
    display_score: float = 0.0
    score_anim_start: float = 0.0
    score_anim_from: float = 0.0
    score_anim_to: float = 0.0
    is_winner: bool = False


class Game:
    def __init__(self, audio: AudioManager, library: SongLibrary, logger: RoundLogger) -> None:
        self.audio = audio
        self.library = library
        self.logger = logger

        self.players = [Player(p["name"]) for p in config.PLAYER_CONFIG]
        self.state = "INIT"
        self.current_song: Song | None = None
        self.round_index = 0
        self.error_message: str | None = None

        self.voting_open_time = 0.0
        self.choosing_started_at = 0.0
        self.pre_reveal_started_at = 0.0
        self.reveal_end_time = 0.0
        self.intermission_end_time = 0.0
        self.reveal_started_at = 0.0

        self.paused = False
        self.pause_started_at = 0.0

    def start_round(self, now: float) -> None:
        self._reset_round_state()
        self.round_index += 1

        failed_paths: set[Path] = set()
        song = self._pick_valid_song(failed_paths)
        # Verify we can find a valid song
        while song is not None:
             # Just check existence, don't play yet
             if song.path.exists():
                 self.current_song = song
                 break
             failed_paths.add(song.path)
             song = self._pick_valid_song(failed_paths)

        if self.current_song is None:
            self.state = "ERROR"
            self.error_message = "Failed to load any songs. Check mp3 support."
            return

        # Start CHOOSING (Roulette)
        self.state = "CHOOSING"
        self.choosing_started_at = now

    def _start_voting(self, now: float) -> None:
        if self.current_song:
             # Try to play the selected song
             if not self.audio.play_music(self.current_song.path):
                 # Fallback if playback fails (should be rare if file exists)
                 print(f"Failed to play {self.current_song.path}")

        self.audio.play_sfx("start")
        self.state = "VOTING"
        self.voting_open_time = now

    def register_vote(self, player_index: int, choice: str, now: float) -> None:
        if self.state != "VOTING":
            return
        if not (0 <= player_index < len(self.players)):
            return
        player = self.players[player_index]
        if player.vote is not None:
            return
        player.vote = choice
        self.audio.play_sfx("lock_in")

    def update(self, now: float) -> None:
        if self.state == "ERROR" or self.paused:
            return

        if self.state == "CHOOSING":
            if (now - self.choosing_started_at) >= config.CHOOSING_DURATION_SECONDS:
                self._start_voting(now)
        elif self.state == "VOTING":
            if self._all_voted() or self._voting_timed_out(now):
                self._start_pre_reveal(now)
        elif self.state == "PRE_REVEAL":
            if (now - self.pre_reveal_started_at) >= config.PRE_REVEAL_DURATION_SECONDS:
                self._perform_reveal(now)
        elif self.state == "REVEAL":
            if now >= self.reveal_end_time:
                self.state = "INTERMISSION"
        elif self.state == "INTERMISSION":
            if now >= self.intermission_end_time:
                self.start_round(now)

    def toggle_pause(self, now: float) -> None:
        if self.state == "ERROR":
            return
        if not self.paused:
            self.paused = True
            self.pause_started_at = now
            self.audio.pause_music()
            return

        self.paused = False
        pause_delta = now - self.pause_started_at
        self.choosing_started_at += pause_delta
        self.voting_open_time += pause_delta
        self.pre_reveal_started_at += pause_delta
        self.reveal_end_time += pause_delta
        self.intermission_end_time += pause_delta
        self.audio.resume_music()

    def skip_round(self, now: float) -> None:
        if self.state == "ERROR":
            return
        self.audio.stop_music()
        self.start_round(now)

    def _all_voted(self) -> bool:
        return all(player.vote is not None for player in self.players)

    def _voting_timed_out(self, now: float) -> bool:
        return (now - self.voting_open_time) >= config.VOTING_TIMEOUT_SECONDS

    def _start_pre_reveal(self, now: float) -> None:
        self.state = "PRE_REVEAL"
        self.pre_reveal_started_at = now
        self.audio.stop_music()
        self.audio.play_sfx("drumroll")

    def _perform_reveal(self, now: float) -> None:
        if self.current_song is None:
            return
        self.state = "REVEAL"
        self.reveal_started_at = now
        self.reveal_end_time = now + config.REVEAL_DURATION_SECONDS
        self.intermission_end_time = self.reveal_end_time + config.INTERMISSION_SECONDS

        correct = self.current_song.category
        self.audio.play_sfx("reveal")

        winners = []
        for player in self.players:
            player.is_winner = player.vote == correct
            if player.is_winner:
                player.score += 1
                player.score_anim_start = now
                player.score_anim_from = player.display_score
                player.score_anim_to = float(player.score)
                winners.append(player)

        if winners:
            self.audio.play_sfx("win")
        else:
            self.audio.play_sfx("lose")

        self._log_round(correct)

    def _log_round(self, correct: str) -> None:
        if self.current_song is None:
            return
        payload = {
            "round_index": self.round_index,
            "track_path": str(self.current_song.path),
            "category": "ai" if correct == "Silicon" else "human",
            "correct_answer": correct,
            "players": [
                {
                    "name": player.name,
                    "vote": player.vote,
                    "correct": player.vote == correct if player.vote else False,
                    "score_after": player.score,
                }
                for player in self.players
            ],
        }
        self.logger.log_round(payload)

    def _reset_round_state(self) -> None:
        for player in self.players:
            player.vote = None
            player.is_winner = False
            if player.display_score == 0.0 and player.score > 0:
                player.display_score = float(player.score)
        self.current_song = None

    def _pick_valid_song(self, failed_paths: Iterable[Path]) -> Song | None:
        return self.library.pick(exclude=failed_paths)


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
    vote_time: float | None = None
    points_delta: int = 0
    display_score: float = 0.0
    score_anim_start: float = 0.0
    score_anim_from: float = 0.0
    score_anim_to: float = 0.0
    is_winner: bool = False
    is_champion: bool = False


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

        self.game_over_started_at = 0.0

        self.paused = False
        self.pause_started_at_real = 0.0
        self.pause_total_seconds = 0.0

    def effective_now(self, real_now: float) -> float:
        """
        Return a pause-aware time value suitable for all game timers/animations.

        While paused, this value does not advance.
        """
        if self.paused:
            return self.pause_started_at_real - self.pause_total_seconds
        return real_now - self.pause_total_seconds

    def set_player_names(self, names: list[str]) -> None:
        """
        Update player display names (in order).

        - Extra provided names are ignored.
        - Blank/whitespace-only names are ignored (default kept).
        """
        cleaned: list[str] = [n.strip() for n in names if n.strip()]
        for i, name in enumerate(cleaned[: len(self.players)]):
            self.players[i].name = name

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
        if self.paused:
            return
        if self.state != "VOTING":
            return
        if not (0 <= player_index < len(self.players)):
            return
        player = self.players[player_index]
        if player.vote is not None:
            return
        player.vote = choice
        player.vote_time = now
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
                if config.TOTAL_ROUNDS > 0 and self.round_index >= config.TOTAL_ROUNDS:
                    self._end_match(now)
                else:
                    self.start_round(now)
        elif self.state == "GAME_OVER":
            return

    def toggle_pause(self, now: float) -> None:
        if self.state == "ERROR":
            return
        if self.state == "VOTING":
            return
        if not self.paused:
            self.paused = True
            self.pause_started_at_real = now
            self.audio.pause_music()
            return

        # Resume.
        self.paused = False
        self.pause_total_seconds += max(0.0, now - self.pause_started_at_real)
        self.audio.resume_music()

    def skip_round(self, now: float) -> None:
        if self.state == "ERROR":
            return
        if self.state == "GAME_OVER":
            self._reset_match(now)
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
                points = self._calculate_speed_points(player.vote_time)
                player.points_delta = points
                player.score += points
                winners.append(player)
            elif player.vote is not None:
                player.points_delta = -config.WRONG_ANSWER_PENALTY
                player.score += player.points_delta
            else:
                player.points_delta = 0

            if player.points_delta != 0:
                player.score_anim_start = now
                player.score_anim_from = player.display_score
                player.score_anim_to = float(player.score)

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
                    "reaction_time_seconds": (
                        player.vote_time - self.voting_open_time
                        if player.vote_time is not None else None
                    ),
                    "correct": player.vote == correct if player.vote else False,
                    "points_delta": player.points_delta,
                    "score_after": player.score,
                }
                for player in self.players
            ],
        }
        self.logger.log_round(payload)

    def _end_match(self, now: float) -> None:
        top_score = max((p.score for p in self.players), default=0)
        for player in self.players:
            player.is_champion = player.score == top_score
        self.game_over_started_at = now
        self.state = "GAME_OVER"

    def _reset_match(self, now: float) -> None:
        for player in self.players:
            player.score = 0
            player.display_score = 0.0
            player.score_anim_start = 0.0
            player.score_anim_from = 0.0
            player.score_anim_to = 0.0
            player.is_champion = False
            player.is_winner = False
            player.vote = None
            player.vote_time = None
            player.points_delta = 0
        self.round_index = 0
        self.current_song = None
        self.state = "INIT"
        self.audio.stop_music()
        self.start_round(now)

    def _calculate_speed_points(self, vote_time: float | None) -> int:
        if vote_time is None:
            return 0
        if config.VOTING_TIMEOUT_SECONDS <= 0:
            return config.SPEED_POINTS_MIN
        elapsed = vote_time - self.voting_open_time
        elapsed = max(0.0, min(config.VOTING_TIMEOUT_SECONDS, elapsed))
        progress = elapsed / config.VOTING_TIMEOUT_SECONDS
        curved = 1.0 - (progress ** config.SPEED_POINTS_EXP)
        points = config.SPEED_POINTS_MIN + (
            (config.SPEED_POINTS_MAX - config.SPEED_POINTS_MIN) * curved
        )
        return int(round(points))

    def current_speed_points(self, now: float) -> int:
        """Points awarded if a player is correct right now."""
        return self._calculate_speed_points(now)

    def speed_points_for_vote_time(self, vote_time: float | None) -> int:
        """Points awarded for a specific vote time."""
        return self._calculate_speed_points(vote_time)

    def _reset_round_state(self) -> None:
        for player in self.players:
            player.vote = None
            player.vote_time = None
            player.points_delta = 0
            player.is_winner = False
            if player.display_score == 0.0 and player.score > 0:
                player.display_score = float(player.score)
        self.current_song = None

    def _pick_valid_song(self, failed_paths: Iterable[Path]) -> Song | None:
        return self.library.pick(exclude=failed_paths)


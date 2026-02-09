from __future__ import annotations

import pygame

from . import config
from .game import Game, Player


class UI:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.large_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)

    def draw(self, game: Game, now: float) -> None:
        self.screen.fill(config.COLORS["background"])

        if game.error_message:
            self._draw_centered(game.error_message, config.COLORS["warning"])
            pygame.display.flip()
            return

        status = "PAUSED" if game.paused else game.state
        status_text = self.large_font.render(f"STATUS: {status}", True, config.COLORS["text"])
        self.screen.blit(status_text, (24, 20))

        if game.current_song:
            track_text = self.small_font.render(
                f"TRACK: {game.current_song.path.name}", True, config.COLORS["muted"]
            )
            self.screen.blit(track_text, (24, 70))

        if game.state == "VOTING":
            remaining = max(0.0, config.VOTING_TIMEOUT_SECONDS - (now - game.voting_open_time))
            countdown = self.large_font.render(f"VOTING: {remaining:0.1f}s", True, config.COLORS["text"])
            self.screen.blit(countdown, (520, 20))
        elif game.state == "REVEAL":
            reveal_text = self.large_font.render("REVEAL", True, config.COLORS["winner"])
            self.screen.blit(reveal_text, (560, 20))

        y_pos = 130
        for player in game.players:
            self._draw_player_row(player, y_pos, game, now)
            y_pos += 110

        pygame.display.flip()

    def _draw_player_row(self, player: Player, y_pos: int, game: Game, now: float) -> None:
        panel_rect = pygame.Rect(24, y_pos, 752, 90)
        panel_color = config.COLORS["panel"]
        if game.state == "REVEAL" and player.is_winner:
            if (now - game.reveal_started_at) <= config.WINNER_HIGHLIGHT_DURATION:
                panel_color = (40, 70, 40)
        pygame.draw.rect(self.screen, panel_color, panel_rect, border_radius=10)

        name_text = self.font.render(player.name, True, config.COLORS["text"])
        self.screen.blit(name_text, (40, y_pos + 12))

        display_score = self._get_display_score(player, now)
        score_text = self.large_font.render(f"{display_score:.0f}", True, config.COLORS["text"])
        self.screen.blit(score_text, (680, y_pos + 20))

        self._draw_vote_indicator(player, y_pos)

    def _draw_vote_indicator(self, player: Player, y_pos: int) -> None:
        silicon_color = config.COLORS["silicon"]
        soul_color = config.COLORS["soul"]
        if player.vote == "Silicon":
            silicon_color = config.COLORS["winner"]
        elif player.vote == "Soul":
            soul_color = config.COLORS["winner"]

        pygame.draw.circle(self.screen, silicon_color, (420, y_pos + 45), 18)
        pygame.draw.circle(self.screen, soul_color, (470, y_pos + 45), 18)

        sil_label = self.small_font.render("AI", True, config.COLORS["text"])
        soul_label = self.small_font.render("Human", True, config.COLORS["text"])
        self.screen.blit(sil_label, (406, y_pos + 70))
        self.screen.blit(soul_label, (445, y_pos + 70))

    def _get_display_score(self, player: Player, now: float) -> float:
        if player.score_anim_start <= 0.0:
            player.display_score = float(player.score)
            return player.display_score

        elapsed = now - player.score_anim_start
        if elapsed >= config.SCORE_ANIM_DURATION:
            player.display_score = float(player.score)
            player.score_anim_start = 0.0
            return player.display_score

        progress = max(0.0, min(1.0, elapsed / config.SCORE_ANIM_DURATION))
        player.display_score = player.score_anim_from + (player.score_anim_to - player.score_anim_from) * progress
        return player.display_score

    def _draw_centered(self, message: str, color: tuple[int, int, int]) -> None:
        text = self.large_font.render(message, True, color)
        rect = text.get_rect(center=(config.WINDOW_SIZE[0] // 2, config.WINDOW_SIZE[1] // 2))
        self.screen.blit(text, rect)


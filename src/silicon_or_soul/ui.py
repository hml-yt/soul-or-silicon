from __future__ import annotations

import math
import random
import pygame

from . import config
from .game import Game, Player


class UI:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self._init_fonts()
        self._init_background()
        
        # Animation state for roulette
        self.roulette_text = "INITIALIZING..."
        self.last_roulette_update = 0.0
        self.roulette_interval = config.ROULETTE_TICK_INTERVAL_START
        
        # Mock data for roulette
        self.roulette_options = [
            "ANALYZING WAVEFORMS...",
            "DECODING SYNTHS...",
            "CHECKING HEARTBEAT...",
            "GENRE: CLASSICAL",
            "GENRE: SYNTHWAVE",
            "GENRE: JAZZ",
            "GENRE: ROCK",
            "LOADING NEURAL NET...",
            "HUMAN OR MACHINE?",
        ]

    def _init_fonts(self) -> None:
        # Helper to try loading fonts
        def get_font(names: list[str], size: int) -> pygame.font.Font:
            for name in names:
                try:
                    return pygame.font.SysFont(name, size)
                except:
                    continue
            return pygame.font.Font(None, size)

        # Scale fonts for 1080p
        self.font_small = get_font(["Arial Rounded MT Bold", "Helvetica", "Arial"], 36)
        self.font_normal = get_font(["Arial Rounded MT Bold", "Helvetica", "Arial"], 48)
        self.font_large = get_font(["Arial Rounded MT Bold", "Helvetica", "Arial"], 72)
        self.font_huge = get_font(["Arial Rounded MT Bold", "Helvetica", "Arial"], 140)

    def _init_background(self) -> None:
        # Pre-render gradient background
        self.bg_surface = pygame.Surface(config.WINDOW_SIZE)
        top_color = config.COLORS["background_top"]
        bottom_color = config.COLORS["background_bottom"]
        
        h = config.WINDOW_SIZE[1]
        for y in range(h):
            ratio = y / h
            r = top_color[0] + (bottom_color[0] - top_color[0]) * ratio
            g = top_color[1] + (bottom_color[1] - top_color[1]) * ratio
            b = top_color[2] + (bottom_color[2] - top_color[2]) * ratio
            pygame.draw.line(self.bg_surface, (int(r), int(g), int(b)), (0, y), (config.WINDOW_SIZE[0], y))

    def draw(self, game: Game, now: float) -> None:
        self.screen.blit(self.bg_surface, (0, 0))

        if game.error_message:
            self._draw_centered(game.error_message, config.COLORS["warning"])
            pygame.display.flip()
            return

        # Draw Header / Status
        self._draw_header(game, now)

        # Draw Main Center Display (Context sensitive)
        self._draw_main_display(game, now)

        # Draw Players
        self._draw_players(game, now)

        pygame.display.flip()

    def _draw_header(self, game: Game, now: float) -> None:
        # Left: Status
        status = "PAUSED" if game.paused else game.state
        status_color = config.COLORS["text"]
        if game.state == "VOTING":
             # Pulse effect
             alpha = 150 + int(105 * abs(math.sin(now * 5)))
             status_color = (*config.COLORS["text"][:3], alpha) # Note: rendering text with alpha is tricky in pygame without surface

        status_surf = self.font_large.render(f"STATUS: {status}", True, config.COLORS["muted"])
        self.screen.blit(status_surf, (50, 40))

        # Right: Timer
        if game.state == "VOTING":
            remaining = max(0.0, config.VOTING_TIMEOUT_SECONDS - (now - game.voting_open_time))
            color = config.COLORS["text"]
            if remaining < 5.0:
                color = config.COLORS["warning"]
            timer_surf = self.font_large.render(f"{remaining:0.1f}s", True, color)
            timer_rect = timer_surf.get_rect(topright=(config.WINDOW_SIZE[0] - 50, 40))
            self.screen.blit(timer_surf, timer_rect)

    def _draw_main_display(self, game: Game, now: float) -> None:
        center_x = config.WINDOW_SIZE[0] // 2
        center_y = 300 # Upper middle

        if game.state == "CHOOSING":
            self._update_roulette(game, now)
            text = self.font_huge.render(self.roulette_text, True, config.COLORS["silicon"])
            rect = text.get_rect(center=(center_x, center_y))
            self.screen.blit(text, rect)
            
            # Subtext
            sub = self.font_normal.render("SELECTING TRACK...", True, config.COLORS["muted"])
            sub_rect = sub.get_rect(center=(center_x, center_y + 80))
            self.screen.blit(sub, sub_rect)

        elif game.state == "VOTING":
             text = self.font_huge.render("LISTEN & VOTE", True, config.COLORS["text"])
             rect = text.get_rect(center=(center_x, center_y))
             self.screen.blit(text, rect)
             
             # if game.current_song:
             #     song_name = game.current_song.path.name
             #     sub = self.font_normal.render(f"Track: {song_name}", True, config.COLORS["muted"])
             #     sub_rect = sub.get_rect(center=(center_x, center_y + 80))
             #     self.screen.blit(sub, sub_rect)

        elif game.state == "PRE_REVEAL":
            # Tension flash
            elapsed = now - game.pre_reveal_started_at
            if int(elapsed * 10) % 2 == 0:
                text = "SILICON?"
                color = config.COLORS["silicon"]
            else:
                text = "SOUL?"
                color = config.COLORS["soul"]
            
            surf = self.font_huge.render(text, True, color)
            rect = surf.get_rect(center=(center_x, center_y))
            self.screen.blit(surf, rect)

        elif game.state == "REVEAL" or game.state == "INTERMISSION":
            if game.current_song:
                is_ai = game.current_song.category == "Silicon"
                text = "SILICON" if is_ai else "SOUL"
                color = config.COLORS["silicon"] if is_ai else config.COLORS["soul"]
                
                # Glow effect (draw multiple times with offset/alpha if possible, or just big)
                surf = self.font_huge.render(text, True, color)
                rect = surf.get_rect(center=(center_x, center_y))
                self.screen.blit(surf, rect)
                
                label = "IT WAS"
                label_surf = self.font_normal.render(label, True, config.COLORS["text"])
                label_rect = label_surf.get_rect(center=(center_x, center_y - 80))
                self.screen.blit(label_surf, label_rect)

    def _update_roulette(self, game: Game, now: float) -> None:
        # Slow down as we approach end
        elapsed = now - game.choosing_started_at
        progress = min(1.0, elapsed / config.CHOOSING_DURATION_SECONDS)
        
        current_interval = config.ROULETTE_TICK_INTERVAL_START + (
            (config.ROULETTE_TICK_INTERVAL_END - config.ROULETTE_TICK_INTERVAL_START) * (progress ** 2)
        )
        
        if now - self.last_roulette_update > current_interval:
            self.last_roulette_update = now
            if progress > 0.9 and game.current_song:
                 # Near end, show actual song name sometimes? Or just keep random until Voting starts
                 self.roulette_text = "LOCKED IN"
            else:
                self.roulette_text = random.choice(self.roulette_options)
            
            game.audio.play_sfx("tick") 

    def _draw_players(self, game: Game, now: float) -> None:
        start_y = 550
        gap = 160
        
        for i, player in enumerate(game.players):
            y = start_y + (i * gap)
            self._draw_player_card(player, y, game, now)

    def _draw_player_card(self, player: Player, y: int, game: Game, now: float) -> None:
        # Card background (Glass effect)
        rect_w, rect_h = 1800, 140
        rect_x = (config.WINDOW_SIZE[0] - rect_w) // 2
        
        # Determine border color
        border_color = config.COLORS["panel_border"]
        glow_color = None
        
        if game.state == "REVEAL" and player.is_winner:
             # Winner pulse
             if (now - game.reveal_started_at) <= config.WINNER_HIGHLIGHT_DURATION:
                 border_color = config.COLORS["winner"]
                 glow_color = config.COLORS["winner"]
        elif player.vote is not None and game.state == "VOTING":
             # Voted highlight
             border_color = config.COLORS["text"]

        # Draw semi-transparent background
        s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
        s.fill((*config.COLORS["panel_bg"], 200)) # 200 alpha
        
        if glow_color:
            pygame.draw.rect(s, glow_color, s.get_rect(), width=4, border_radius=15)
        else:
            pygame.draw.rect(s, border_color, s.get_rect(), width=2, border_radius=15)
            
        self.screen.blit(s, (rect_x, y))

        # Player Name
        name_surf = self.font_normal.render(player.name, True, config.COLORS["text"])
        self.screen.blit(name_surf, (rect_x + 40, y + 50))

        # Score
        display_score = self._get_display_score(player, now)
        score_surf = self.font_large.render(f"{display_score:.0f}", True, config.COLORS["text"])
        score_rect = score_surf.get_rect(midright=(rect_x + rect_w - 60, y + 70))
        self.screen.blit(score_surf, score_rect)

        # Vote Indicators (Center of card)
        center_card_x = rect_x + rect_w // 2
        self._draw_vote_circles(player, center_card_x, y + 70)

    def _draw_vote_circles(self, player: Player, x: int, y: int) -> None:
        radius = 30
        gap = 80
        
        silicon_x = x - gap // 2
        soul_x = x + gap // 2
        
        # Default colors (dim)
        sil_color = (*config.COLORS["silicon"][:3], 50) # Dim
        soul_color = (*config.COLORS["soul"][:3], 50)  # Dim
        
        # Active colors (if voted)
        if player.vote == "Silicon":
            sil_color = config.COLORS["silicon"]
        elif player.vote == "Soul":
            soul_color = config.COLORS["soul"]
            
        # Draw Silicon Circle
        # Note: Pygame draw.circle doesn't support alpha directly on main screen unless blitting a surface
        # So we use a helper surface
        self._draw_circle_alpha(sil_color, (silicon_x, y), radius)
        self._draw_circle_alpha(soul_color, (soul_x, y), radius)
        
        # Labels
        sil_label = self.font_small.render("AI", True, config.COLORS["text"])
        sil_rect = sil_label.get_rect(center=(silicon_x, y + radius + 25))
        self.screen.blit(sil_label, sil_rect)

        soul_label = self.font_small.render("Human", True, config.COLORS["text"])
        soul_rect = soul_label.get_rect(center=(soul_x, y + radius + 25))
        self.screen.blit(soul_label, soul_rect)

    def _draw_circle_alpha(self, color: tuple, center: tuple, radius: int) -> None:
        target_rect = pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
        shape_surf = pygame.Surface(target_rect.size, pygame.SRCALPHA)
        
        # If color has 4 components, use it, else assume 255 alpha
        c = color if len(color) == 4 else (*color, 255)
        
        pygame.draw.circle(shape_surf, c, (radius, radius), radius)
        self.screen.blit(shape_surf, target_rect)

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
        # Ease out cubic
        progress = 1 - (1 - progress) ** 3
        player.display_score = player.score_anim_from + (player.score_anim_to - player.score_anim_from) * progress
        return player.display_score

    def _draw_centered(self, message: str, color: tuple[int, int, int]) -> None:
        text = self.font_large.render(message, True, color)
        rect = text.get_rect(center=(config.WINDOW_SIZE[0] // 2, config.WINDOW_SIZE[1] // 2))
        self.screen.blit(text, rect)

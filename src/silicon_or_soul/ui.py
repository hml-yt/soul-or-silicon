"""Game-show quality UI renderer for Silicon or Soul."""
from __future__ import annotations

import math
import random
import pygame

from . import config
from .game import Game, Player
from .particles import ParticleSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lerp_color(a: tuple, b: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def _ease_out_elastic(t: float) -> float:
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    p = 0.4
    return pow(2, -10 * t) * math.sin((t - p / 4) * (2 * math.pi) / p) + 1


def _pulse(now: float, speed: float = 3.0, lo: float = 0.4, hi: float = 1.0) -> float:
    """Returns a value oscillating between lo and hi."""
    t = (math.sin(now * speed) + 1) / 2
    return lo + (hi - lo) * t


def _get_font(size: int) -> pygame.font.Font:
    for name in config.FONT_NAMES:
        try:
            f = pygame.font.SysFont(name, size)
            if f:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


# ---------------------------------------------------------------------------
# Background Stars
# ---------------------------------------------------------------------------

class _Star:
    __slots__ = ("x", "y", "base_size", "speed", "phase")
    def __init__(self) -> None:
        self.x = random.randint(0, config.WINDOW_SIZE[0])
        self.y = random.randint(0, config.WINDOW_SIZE[1])
        self.base_size = random.uniform(1.0, 3.0)
        self.speed = random.uniform(0.3, 1.2)
        self.phase = random.uniform(0, math.tau)


# ---------------------------------------------------------------------------
# Main UI Class
# ---------------------------------------------------------------------------

class UI:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.W, self.H = config.WINDOW_SIZE

        # Fonts
        self.font_tiny  = _get_font(28)
        self.font_small = _get_font(38)
        self.font_med   = _get_font(52)
        self.font_large = _get_font(80)
        self.font_huge  = _get_font(160)
        self.font_title = _get_font(56)

        # Pre-render gradient background
        self._bg = self._make_gradient()

        # Stars
        self._stars = [_Star() for _ in range(config.BG_STAR_COUNT)]

        # Particles
        self.particles = ParticleSystem()
        self._last_time = 0.0

        # Roulette state
        self._roulette_text = "..."
        self._roulette_last_tick = 0.0
        self._roulette_options = [
            "SCANNING AUDIO DNA",
            "SAMPLING FREQUENCIES",
            "RUNNING TURING TEST",
            "DETECTING SOUL",
            "NEURAL ANALYSIS",
            "FREQUENCY SWEEP",
            "HARMONIC CHECK",
            "PATTERN MATCHING",
            "DEEP LISTENING",
            "GENRE: ???",
        ]

        # Screen-shake state
        self._shake_amount = 0.0
        self._shake_decay = 8.0

        # Track state changes for particle bursts
        self._prev_state = ""
        self._confetti_fired = False
        self._vote_particle_state: dict[int, bool] = {}

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _make_gradient(self) -> pygame.Surface:
        surf = pygame.Surface(config.WINDOW_SIZE)
        top = config.COLORS["bg_top"]
        bot = config.COLORS["bg_bottom"]
        for y in range(self.H):
            t = y / self.H
            c = _lerp_color(top, bot, t)
            pygame.draw.line(surf, c, (0, y), (self.W, y))
        return surf

    def _draw_background(self, now: float) -> None:
        self.screen.blit(self._bg, (0, 0))
        # Animated stars
        for s in self._stars:
            brightness = _pulse(now + s.phase, s.speed, 0.2, 1.0)
            size = max(1, int(s.base_size * brightness))
            alpha = int(180 * brightness)
            color = (200, 210, 255, alpha)
            ss = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ss, color, (size, size), size)
            self.screen.blit(ss, (s.x - size, s.y - size))

    # ------------------------------------------------------------------
    # Neon line / divider
    # ------------------------------------------------------------------

    def _draw_neon_line(self, y: int, color: tuple, width: int = 2, glow_radius: int = 6) -> None:
        # Glow
        glow_surf = pygame.Surface((self.W, glow_radius * 2), pygame.SRCALPHA)
        for i in range(glow_radius):
            alpha = int(40 * (1 - i / glow_radius))
            pygame.draw.line(glow_surf, (*color[:3], alpha),
                             (0, glow_radius + i), (self.W, glow_radius + i))
            pygame.draw.line(glow_surf, (*color[:3], alpha),
                             (0, glow_radius - i), (self.W, glow_radius - i))
        self.screen.blit(glow_surf, (0, y - glow_radius))
        pygame.draw.line(self.screen, color, (0, y), (self.W, y), width)

    # ------------------------------------------------------------------
    # Glass panel
    # ------------------------------------------------------------------

    def _draw_glass_panel(self, rect: pygame.Rect, border_color: tuple,
                          glow_color: tuple | None = None, alpha: int = 180) -> None:
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        # Fill
        s.fill((*config.COLORS["panel_bg"][:3], alpha))
        # Border
        bw = 3 if glow_color else 2
        bc = glow_color or border_color
        pygame.draw.rect(s, (*bc[:3], 220), s.get_rect(), width=bw, border_radius=16)
        self.screen.blit(s, rect.topleft)

        # Outer glow (if winner/active)
        if glow_color:
            gs = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*glow_color[:3], 35),
                             gs.get_rect(), width=8, border_radius=20)
            self.screen.blit(gs, (rect.x - 8, rect.y - 8))

    # ------------------------------------------------------------------
    # Glow text
    # ------------------------------------------------------------------

    def _draw_glow_text(self, text: str, font: pygame.font.Font,
                        color: tuple, cx: int, cy: int, glow_layers: int = 3) -> None:
        # Glow layers (bigger, dimmer copies behind)
        for i in range(glow_layers, 0, -1):
            scale = 1.0 + i * 0.02
            alpha = max(10, 60 // i)
            glow_surf = font.render(text, True, color)
            gw = int(glow_surf.get_width() * scale)
            gh = int(glow_surf.get_height() * scale)
            glow_surf = pygame.transform.smoothscale(glow_surf, (gw, gh))
            glow_alpha = pygame.Surface((gw, gh), pygame.SRCALPHA)
            glow_alpha.blit(glow_surf, (0, 0))
            glow_alpha.set_alpha(alpha)
            self.screen.blit(glow_alpha,
                             glow_alpha.get_rect(center=(cx, cy)))

        # Main text
        main_surf = font.render(text, True, color)
        self.screen.blit(main_surf, main_surf.get_rect(center=(cx, cy)))

    # ------------------------------------------------------------------
    # Progress / Timer bar
    # ------------------------------------------------------------------

    def _draw_timer_bar(self, progress: float, y: int, color_a: tuple, color_b: tuple) -> None:
        """progress: 0.0 (empty) to 1.0 (full)."""
        bar_w = 1600
        bar_h = 12
        x = (self.W - bar_w) // 2
        border_r = pygame.Rect(x, y, bar_w, bar_h)

        # Background
        bg = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bg.fill((255, 255, 255, 20))
        self.screen.blit(bg, (x, y))

        # Fill
        fill_w = max(0, int(bar_w * progress))
        if fill_w > 0:
            fill_color = _lerp_color(color_b, color_a, progress)
            fill_s = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            fill_s.fill((*fill_color[:3], 200))
            self.screen.blit(fill_s, (x, y))

            # Glow on tip
            tip_x = x + fill_w
            gs = pygame.Surface((20, bar_h + 8), pygame.SRCALPHA)
            gs.fill((*fill_color[:3], 80))
            self.screen.blit(gs, (tip_x - 10, y - 4))

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------

    def draw(self, game: Game, now: float) -> None:
        dt = now - self._last_time if self._last_time > 0 else 1 / 60
        self._last_time = now

        # Update particles
        self.particles.update(dt)

        # Screen shake decay
        self._shake_amount *= max(0, 1 - self._shake_decay * dt)
        shake_x = random.uniform(-self._shake_amount, self._shake_amount)
        shake_y = random.uniform(-self._shake_amount, self._shake_amount)

        # Background
        self._draw_background(now)

        # State-change triggers
        self._handle_state_transitions(game, now)

        # Error screen
        if game.error_message:
            self._draw_glow_text(game.error_message, self.font_large,
                                 config.COLORS["warning"], self.W // 2, self.H // 2)
            self.particles.draw(self.screen, shake_x, shake_y)
            pygame.display.flip()
            return

        # Title bar
        self._draw_title_bar(game, now)

        # Main center content
        self._draw_center(game, now)

        # Players
        self._draw_players(game, now, shake_x, shake_y)

        # Particles on top
        self.particles.draw(self.screen, shake_x, shake_y)

        pygame.display.flip()

    # ------------------------------------------------------------------
    # State transition hooks (fire particles, shake, etc.)
    # ------------------------------------------------------------------

    def _handle_state_transitions(self, game: Game, now: float) -> None:
        if game.state != self._prev_state:
            if game.state == "REVEAL":
                # Big confetti burst + screen shake
                self.particles.emit_confetti(self.W / 2, self.H / 3, config.CONFETTI_BURST_COUNT)
                self._shake_amount = 18.0
                self._confetti_fired = True
            elif game.state == "PRE_REVEAL":
                self._shake_amount = 6.0
            elif game.state == "CHOOSING":
                self._roulette_text = "..."
                self._roulette_last_tick = 0.0
                self._confetti_fired = False
                self._vote_particle_state = {}
            self._prev_state = game.state

        # Vote lock-in particles
        if game.state == "VOTING":
            for i, player in enumerate(game.players):
                if player.vote and not self._vote_particle_state.get(i, False):
                    self._vote_particle_state[i] = True
                    # Emit at the player card center area
                    card_cy = 560 + i * 160 + 70
                    color = config.COLORS["silicon"] if player.vote == "Silicon" else config.COLORS["soul"]
                    self.particles.emit_vote_lock(self.W / 2, card_cy, color)

    # ------------------------------------------------------------------
    # Title bar
    # ------------------------------------------------------------------

    def _draw_title_bar(self, game: Game, now: float) -> None:
        # Show title + round number
        title = "SILICON  OR  SOUL"
        self._draw_glow_text(title, self.font_title,
                             config.COLORS["text"], self.W // 2, 45, glow_layers=2)

        # Round badge
        round_text = f"ROUND {game.round_index}"
        rt_surf = self.font_small.render(round_text, True, config.COLORS["gold"])
        self.screen.blit(rt_surf, rt_surf.get_rect(midright=(self.W - 60, 45)))

        # Neon divider
        self._draw_neon_line(85, config.COLORS["panel_glow"], width=1, glow_radius=4)

        # Status text (left side, below divider)
        status = "PAUSED" if game.paused else game.state.replace("_", " ")
        status_color = config.COLORS["muted"]
        if game.state == "VOTING":
            status_color = _lerp_color(config.COLORS["muted"], config.COLORS["silicon"],
                                       _pulse(now, 4.0, 0.3, 1.0))
        elif game.state == "REVEAL":
            status_color = config.COLORS["winner"]

        st_surf = self.font_small.render(status, True, status_color)
        self.screen.blit(st_surf, (60, 100))

    # ------------------------------------------------------------------
    # Center display
    # ------------------------------------------------------------------

    def _draw_center(self, game: Game, now: float) -> None:
        cx = self.W // 2
        cy = 300

        if game.state == "CHOOSING":
            self._draw_choosing(game, now, cx, cy)
        elif game.state == "VOTING":
            self._draw_voting(game, now, cx, cy)
        elif game.state == "PRE_REVEAL":
            self._draw_pre_reveal(game, now, cx, cy)
        elif game.state in ("REVEAL", "INTERMISSION"):
            self._draw_reveal(game, now, cx, cy)

    def _draw_choosing(self, game: Game, now: float, cx: int, cy: int) -> None:
        # Roulette text cycling
        elapsed = now - game.choosing_started_at
        progress = min(1.0, elapsed / config.CHOOSING_DURATION_SECONDS)

        interval = config.ROULETTE_TICK_INTERVAL_START + (
            (config.ROULETTE_TICK_INTERVAL_END - config.ROULETTE_TICK_INTERVAL_START) * (progress ** 2)
        )

        if now - self._roulette_last_tick > interval:
            self._roulette_last_tick = now
            if progress > 0.92:
                self._roulette_text = "LOCKED IN"
            else:
                self._roulette_text = random.choice(self._roulette_options)
            game.audio.play_sfx("tick")

        # Animated scale
        scale = 1.0 + 0.05 * math.sin(now * 12)
        color = _lerp_color(config.COLORS["silicon"], config.COLORS["soul"], _pulse(now, 6.0))
        self._draw_glow_text(self._roulette_text, self.font_large, color, cx, cy, glow_layers=4)

        # Subtext
        dots = "." * (1 + int(now * 3) % 3)
        sub = f"SELECTING TRACK{dots}"
        sub_surf = self.font_small.render(sub, True, config.COLORS["muted"])
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 65)))

        # Progress bar
        self._draw_timer_bar(1.0 - progress, cy + 100,
                             config.COLORS["silicon"], config.COLORS["soul"])

    def _draw_voting(self, game: Game, now: float, cx: int, cy: int) -> None:
        remaining = max(0.0, config.VOTING_TIMEOUT_SECONDS - (now - game.voting_open_time))
        progress = remaining / config.VOTING_TIMEOUT_SECONDS

        # Main text with pulse
        alpha_pulse = _pulse(now, 2.5, 0.7, 1.0)
        color = tuple(int(c * alpha_pulse) for c in config.COLORS["text"][:3])
        self._draw_glow_text("LISTEN & VOTE", self.font_huge, color, cx, cy - 10, glow_layers=2)

        # Countdown
        timer_color = config.COLORS["text"]
        if remaining < 5.0:
            timer_color = _lerp_color(config.COLORS["warning"], config.COLORS["text"],
                                      _pulse(now, 8.0, 0.0, 1.0))
        timer_text = f"{remaining:.1f}s"
        self._draw_glow_text(timer_text, self.font_large, timer_color,
                             self.W - 120, 110, glow_layers=2)

        # Timer bar
        bar_color_a = config.COLORS["silicon"]
        bar_color_b = config.COLORS["warning"]
        self._draw_timer_bar(progress, cy + 85, bar_color_a, bar_color_b)

    def _draw_pre_reveal(self, game: Game, now: float, cx: int, cy: int) -> None:
        elapsed = now - game.pre_reveal_started_at
        progress = min(1.0, elapsed / config.PRE_REVEAL_DURATION_SECONDS)

        # Flash frequency increases as we approach the reveal
        freq = 3 + progress * 20
        show_silicon = math.sin(now * freq) > 0

        if show_silicon:
            text, color = "SILICON ?", config.COLORS["silicon"]
        else:
            text, color = "SOUL ?", config.COLORS["soul"]

        # Scale up as tension builds
        scale_factor = 1.0 + progress * 0.15
        font_size = int(160 * scale_factor)
        font = _get_font(min(font_size, 220))
        self._draw_glow_text(text, font, color, cx, cy, glow_layers=5)

        # Dim overlay at edges (vignette effect)
        vig = pygame.Surface(config.WINDOW_SIZE, pygame.SRCALPHA)
        alpha_v = int(80 * progress)
        vig.fill((0, 0, 0, alpha_v))
        # Cut out a bright center circle
        pygame.draw.circle(vig, (0, 0, 0, 0), (cx, cy), int(500 * (1.2 - progress * 0.3)))
        self.screen.blit(vig, (0, 0))

        # Progress bar (tension)
        self._draw_timer_bar(progress, cy + 100,
                             config.COLORS["soul"], config.COLORS["silicon"])

    def _draw_reveal(self, game: Game, now: float, cx: int, cy: int) -> None:
        if not game.current_song:
            return

        is_ai = game.current_song.category == "Silicon"
        answer = "SILICON" if is_ai else "SOUL"
        color = config.COLORS["silicon"] if is_ai else config.COLORS["soul"]

        elapsed = now - game.reveal_started_at

        # Entrance animation: scale from 2x down to 1x with elastic ease
        t = min(1.0, elapsed / 0.6)
        scale = 1.0 + (1.0 - _ease_out_elastic(t)) * 0.8
        font_size = int(160 * scale)
        font = _get_font(min(font_size, 280))

        # "IT WAS" label
        if elapsed > 0.15:
            label_alpha = min(255, int((elapsed - 0.15) / 0.3 * 255))
            label_surf = self.font_med.render("THE ANSWER IS", True, config.COLORS["text"])
            label_surf.set_alpha(label_alpha)
            self.screen.blit(label_surf, label_surf.get_rect(center=(cx, cy - 100)))

        # Main answer with big glow
        self._draw_glow_text(answer, font, color, cx, cy, glow_layers=6)

        # Winner/loser indicators under answer
        if elapsed > 0.8:
            winners = [p for p in game.players if p.is_winner]
            if winners:
                txt = f"{len(winners)} CORRECT!"
                self._draw_glow_text(txt, self.font_med, config.COLORS["winner"],
                                     cx, cy + 90, glow_layers=2)
            else:
                self._draw_glow_text("NOBODY GOT IT!", self.font_med,
                                     config.COLORS["loser"], cx, cy + 90, glow_layers=2)

    # ------------------------------------------------------------------
    # Player cards
    # ------------------------------------------------------------------

    def _draw_players(self, game: Game, now: float,
                      shake_x: float, shake_y: float) -> None:
        start_y = 540
        gap = 155

        for i, player in enumerate(game.players):
            y = start_y + i * gap
            self._draw_player_card(player, i, int(y + shake_y), game, now)

    def _draw_player_card(self, player: Player, idx: int, y: int,
                          game: Game, now: float) -> None:
        card_w, card_h = 1700, 135
        card_x = (self.W - card_w) // 2

        # Determine card style
        border_color = config.COLORS["panel_border"]
        glow_color = None

        if game.state == "REVEAL" and player.is_winner:
            elapsed = now - game.reveal_started_at
            if elapsed <= config.WINNER_HIGHLIGHT_DURATION:
                pulse = _pulse(now, 6.0, 0.5, 1.0)
                glow_color = tuple(int(c * pulse) for c in config.COLORS["winner"][:3])
                border_color = glow_color
        elif game.state == "REVEAL" and not player.is_winner and player.vote is not None:
            border_color = config.COLORS["loser"]
        elif player.vote is not None and game.state == "VOTING":
            vote_color = config.COLORS["silicon"] if player.vote == "Silicon" else config.COLORS["soul"]
            border_color = vote_color

        rect = pygame.Rect(card_x, y, card_w, card_h)
        self._draw_glass_panel(rect, border_color, glow_color)

        # Player number badge (inside the card)
        badge_x = card_x + 55
        badge_y = y + card_h // 2
        badge_r = 30
        badge_color = config.COLORS["panel_glow"]
        s = pygame.Surface((badge_r * 2, badge_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*badge_color[:3], 80), (badge_r, badge_r), badge_r)
        self.screen.blit(s, (badge_x - badge_r, badge_y - badge_r))
        num_surf = self.font_med.render(str(idx + 1), True, config.COLORS["text"])
        self.screen.blit(num_surf, num_surf.get_rect(center=(badge_x, badge_y)))

        # Player name
        name_surf = self.font_med.render(player.name, True, config.COLORS["text"])
        self.screen.blit(name_surf, (card_x + 110, y + card_h // 2 - name_surf.get_height() // 2))

        # Vote indicators (center)
        center_x = card_x + card_w // 2
        self._draw_vote_indicators(player, center_x, y + card_h // 2, game, now)

        # Score (right side)
        display_score = self._get_display_score(player, now)
        score_text = f"{display_score:.0f}"
        score_color = config.COLORS["text"]
        if game.state == "REVEAL" and player.is_winner:
            score_color = config.COLORS["winner"]
        score_surf = self.font_large.render(score_text, True, score_color)
        self.screen.blit(score_surf, score_surf.get_rect(midright=(card_x + card_w - 50,
                                                                    y + card_h // 2)))

    def _draw_vote_indicators(self, player: Player, cx: int, cy: int,
                              game: Game, now: float) -> None:
        gap = 160
        si_x = cx - gap // 2
        so_x = cx + gap // 2
        radius = 32

        # Silicon indicator
        si_active = player.vote == "Silicon"
        si_color = config.COLORS["silicon"] if si_active else config.COLORS["silicon_dim"]
        si_alpha = 255 if si_active else 60
        self._draw_indicator_circle(si_x, cy, radius, si_color, si_alpha, si_active, now)
        lbl = self.font_small.render("AI", True,
                                     config.COLORS["silicon"] if si_active else config.COLORS["muted"])
        self.screen.blit(lbl, lbl.get_rect(center=(si_x, cy + radius + 22)))

        # Soul indicator
        so_active = player.vote == "Soul"
        so_color = config.COLORS["soul"] if so_active else config.COLORS["soul_dim"]
        so_alpha = 255 if so_active else 60
        self._draw_indicator_circle(so_x, cy, radius, so_color, so_alpha, so_active, now)
        lbl = self.font_small.render("HUMAN", True,
                                     config.COLORS["soul"] if so_active else config.COLORS["muted"])
        self.screen.blit(lbl, lbl.get_rect(center=(so_x, cy + radius + 22)))

        # "VS" between them
        vs = self.font_tiny.render("VS", True, config.COLORS["muted"])
        self.screen.blit(vs, vs.get_rect(center=(cx, cy)))

    def _draw_indicator_circle(self, cx: int, cy: int, radius: int,
                               color: tuple, alpha: int, active: bool,
                               now: float) -> None:
        size = radius * 2
        s = pygame.Surface((size + 16, size + 16), pygame.SRCALPHA)
        center = (size // 2 + 8, size // 2 + 8)

        # Outer glow if active
        if active:
            glow_pulse = _pulse(now, 5.0, 0.3, 0.8)
            glow_r = int(radius * 1.4)
            pygame.draw.circle(s, (*color[:3], int(60 * glow_pulse)), center, glow_r)

        pygame.draw.circle(s, (*color[:3], alpha), center, radius)
        # Inner highlight
        pygame.draw.circle(s, (255, 255, 255, 30 if active else 10), center, radius - 4)

        self.screen.blit(s, (cx - size // 2 - 8, cy - size // 2 - 8))

    # ------------------------------------------------------------------
    # Score animation
    # ------------------------------------------------------------------

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
        progress = _ease_out_cubic(progress)
        player.display_score = (player.score_anim_from +
                                (player.score_anim_to - player.score_anim_from) * progress)
        return player.display_score

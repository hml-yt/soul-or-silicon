"""Lightweight particle system for visual effects."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from . import config


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float          # seconds remaining
    max_life: float
    color: tuple
    size: float
    gravity: float = 0.0
    drag: float = 0.98
    kind: str = "spark"  # spark | confetti | star


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []

    def update(self, dt: float) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            p.vx *= p.drag
            p.vy *= p.drag
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface, offset_x: float = 0, offset_y: float = 0) -> None:
        for p in self.particles:
            ratio = max(0.0, p.life / p.max_life)
            alpha = int(255 * ratio)
            size = max(1, int(p.size * ratio))
            px = int(p.x + offset_x)
            py = int(p.y + offset_y)

            if p.kind == "confetti":
                self._draw_confetti(surface, px, py, size, p.color, alpha)
            elif p.kind == "star":
                self._draw_star_particle(surface, px, py, size, p.color, alpha)
            else:
                self._draw_spark(surface, px, py, size, p.color, alpha)

    def emit_confetti(self, cx: float, cy: float, count: int | None = None) -> None:
        count = count or config.CONFETTI_BURST_COUNT
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(200, 800)
            self.particles.append(Particle(
                x=cx + random.uniform(-20, 20),
                y=cy + random.uniform(-20, 20),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - random.uniform(100, 300),
                life=random.uniform(1.5, 3.5),
                max_life=3.5,
                color=random.choice(config.CONFETTI_COLORS),
                size=random.uniform(6, 14),
                gravity=400,
                drag=0.97,
                kind="confetti",
            ))

    def emit_sparks(self, cx: float, cy: float, color: tuple, count: int = 30) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(100, 500)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.uniform(0.3, 1.0),
                max_life=1.0,
                color=color,
                size=random.uniform(3, 8),
                gravity=200,
                drag=0.95,
                kind="spark",
            ))

    def emit_vote_lock(self, cx: float, cy: float, color: tuple) -> None:
        """Small burst when a player locks in their vote."""
        for _ in range(15):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(50, 200)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.uniform(0.4, 0.8),
                max_life=0.8,
                color=color,
                size=random.uniform(3, 6),
                gravity=0,
                drag=0.92,
                kind="spark",
            ))

    def emit_champion_burst(self, cx: float, cy: float, count: int = 180) -> None:
        """Dramatic upward confetti fountain for the champion reveal."""
        champion_colors = [
            (255, 215, 0),    # gold
            (255, 180, 0),    # amber
            (50, 255, 80),    # winner green
            (255, 255, 200),  # bright white-gold
            (255, 100, 0),    # orange
        ]
        for _ in range(count):
            # Biased upward
            angle = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
            speed = random.uniform(300, 1000)
            self.particles.append(Particle(
                x=cx + random.uniform(-40, 40),
                y=cy + random.uniform(-10, 10),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - random.uniform(150, 400),
                life=random.uniform(2.0, 4.5),
                max_life=4.5,
                color=random.choice(champion_colors),
                size=random.uniform(7, 16),
                gravity=350,
                drag=0.97,
                kind="confetti",
            ))

    def emit_champion_drizzle(self, screen_w: float) -> None:
        """Gentle ongoing confetti drizzle from the top of the screen."""
        champion_colors = [
            (255, 215, 0),
            (50, 255, 80),
            (255, 180, 0),
            (255, 255, 200),
        ]
        for _ in range(3):
            self.particles.append(Particle(
                x=random.uniform(0, screen_w),
                y=random.uniform(-20, 0),
                vx=random.uniform(-30, 30),
                vy=random.uniform(40, 120),
                life=random.uniform(2.0, 4.0),
                max_life=4.0,
                color=random.choice(champion_colors),
                size=random.uniform(4, 10),
                gravity=60,
                drag=0.99,
                kind="confetti",
            ))

    # --- draw helpers ---

    @staticmethod
    def _draw_spark(surface: pygame.Surface, x: int, y: int, size: int, color: tuple, alpha: int) -> None:
        if alpha < 10:
            return
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color[:3], alpha), (size, size), size)
        surface.blit(s, (x - size, y - size))

    @staticmethod
    def _draw_confetti(surface: pygame.Surface, x: int, y: int, size: int, color: tuple, alpha: int) -> None:
        if alpha < 10:
            return
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((*color[:3], alpha))
        surface.blit(s, (x - size // 2, y - size // 2))

    @staticmethod
    def _draw_star_particle(surface: pygame.Surface, x: int, y: int, size: int, color: tuple, alpha: int) -> None:
        if alpha < 10:
            return
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        # Simple 4-point star
        center = size
        pts = []
        for i in range(8):
            angle = math.pi / 4 * i
            r = size if i % 2 == 0 else size // 3
            pts.append((center + math.cos(angle) * r, center + math.sin(angle) * r))
        pygame.draw.polygon(s, (*color[:3], alpha), pts)
        surface.blit(s, (x - size, y - size))

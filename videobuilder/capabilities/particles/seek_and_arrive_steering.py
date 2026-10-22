"""Seek and arrive steering: agents with momentum turn toward a target, head
for it at full speed, then brake smoothly inside a slowing radius so they
come to rest on it instead of overshooting -- the classic steering behaviour."""
import math
from functools import lru_cache

from .. import _demo as demo
from ..schema import Technique


def seek_and_arrive(start, target, t, velocity=(0.0, 0.0), max_speed=900.0, max_force=2600.0,
                    slow_radius=300.0, agility=12.0, step=1 / 120):
    """Where an agent starting at `start` with `velocity` (px/s) is after `t`
    seconds of steering toward `target`. Returns `(x, y, vx, vy)`.

    Each step the agent wants to move straight at the target at `max_speed`,
    scaled down linearly inside `slow_radius` (zero on the target: arrive); the
    steering force is that wish minus its current velocity, times `agility`
    (per second), capped at `max_force` (px/s^2). A low `max_force` gives wide
    curving turns, a high one tight ones; `agility` near `4 * max_speed /
    slow_radius` or above lands without overshoot. Pure: integrated from 0 in
    `step`-second steps, so any `t` can be asked for on its own."""
    x, y = start
    vx, vy = velocity
    tx, ty = target
    s = 0.0
    while s < t:
        h = min(step, t - s)
        dx, dy = tx - x, ty - y
        d = math.hypot(dx, dy)
        speed = max_speed * min(1.0, d / slow_radius)
        wx, wy = (dx / d * speed, dy / d * speed) if d > 1e-9 else (0.0, 0.0)
        fx, fy = (wx - vx) * agility, (wy - vy) * agility
        f = math.hypot(fx, fy)
        if f > max_force:
            fx, fy = fx / f * max_force, fy / f * max_force
        vx, vy = vx + fx * h, vy + fy * h
        v = math.hypot(vx, vy)
        if v > max_speed:
            vx, vy = vx / v * max_speed, vy / v * max_speed
        x, y = x + vx * h, y + vy * h
        s += h
    return x, y, vx, vy


TARGET = (demo.W * 0.66, demo.H * 0.5)
SLOW = 180
# (start, initial velocity, slot offset from the target, colour): each agent is
# launched off-axis, swings round toward its slot, then eases in to rest.
AGENTS = (
    ((70, 70), (260, -160), (0, -24), demo.ACCENT),
    ((50, 280), (160, 60), (-24, 0), demo.TEAL),
    ((100, 480), (300, 140), (0, 24), demo.ACCENT),
    ((330, 500), (-200, 200), (24, 0), demo.TEAL),
    ((300, 40), (-220, -100), (0, 0), demo.INK),
)
TRAIL = 14  # trail dots, one every few frames, so their spacing shows the speed
GAP = 3


@lru_cache(maxsize=None)
def _at(i, n):
    start, vel, (ox, oy), _ = AGENTS[i]
    t = max(0.0, n / demo.FPS - 0.3)
    return seek_and_arrive(start, (TARGET[0] + ox, TARGET[1] + oy), t, velocity=vel, max_speed=600,
                           max_force=1000, slow_radius=SLOW, agility=14)


def draw(n, cv):
    tx, ty = TARGET
    # the target and its slowing radius
    cv.arc(tx, ty, SLOW, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.25)
    cv.arc(tx, ty, 46, 0, 2 * math.pi, demo.MUTED, width=3, alpha=0.7)
    for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        cv.line(tx + a * 40, ty + b * 40, tx + a * 56, ty + b * 56, demo.MUTED, width=3, alpha=0.7)
    for i, (*_, color) in enumerate(AGENTS):
        for k in range(TRAIL, 0, -1):
            m = n - k * GAP
            if m >= 0:
                px, py, _, _ = _at(i, m)
                demo.dot(cv, px, py, 3, color=color, alpha=0.5 * (1 - k / (TRAIL + 1)))
        x, y, vx, vy = _at(i, n)
        v = math.hypot(vx, vy)
        if v > 20:  # a short heading tick shows which way it is steering
            cv.line(x, y, x + vx / v * (12 + v * 0.03), y + vy / v * (12 + v * 0.03), color, width=2)
        demo.dot(cv, x, y, 10, color=color)
        cv.mark(f'agent{i}', x - 10, y - 10, 20, 20)


TECHNIQUE = Technique(
    id='seek-and-arrive-steering',
    name='Seek and arrive steering',
    family='particles',
    group='Swarms & agents',
    aliases=('steering behaviors', 'seek steering', 'arrival', 'arrive behavior'),
    definition='Moving agents curve round to head for a target at full speed, then brake gently once '
               'they get close so each one glides to a stop right on it.',
    phrasings=('have the dots home in on the target and ease to a stop on it',
               'make them chase the point but slow down as they get there instead of overshooting',
               'little agents steering toward a goal and settling onto it'),
    related=('follow-through', 'bounce-ease-in', 'settle', 'slow-in-and-slow-out', 'spotlight-follow',
             'path-follow-motion'),
    api=('videobuilder.techniques.particles.seek_and_arrive_steering.seek_and_arrive',),
    demo=lambda: demo.film(draw),
)

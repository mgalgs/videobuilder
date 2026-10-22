"""Wind field: a drift of particles pushed by a wind whose direction and
strength change from place to place and moment to moment, so gusts sweep
through and bend the whole stream."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def wind(direction=0.0, speed=240.0, swirl=0.5, gust=0.8, wavelength=520.0, gust_speed=420.0, seed=0):
    """A wind field: returns `w(x, y, t) -> (vx, vy)` in px/s.

    The wind blows towards `direction` (radians, 0 = right, pi/2 = down) at
    about `speed`. `swirl` (radians) is how far its heading wanders across
    space and time; `gust` (0 -> 1) how much its strength pulses, in bands
    `wavelength` px apart that travel downwind at `gust_speed` px/s. The
    same `seed` gives the same field. Pass `speed` as a callable `speed(t)`
    to let the wind rise and fall over time."""
    rnd = random.Random(seed)
    waves = [(rnd.uniform(0.6, 1.4) / wavelength, rnd.uniform(0.6, 1.4) / wavelength,
              rnd.uniform(0, 2 * math.pi), rnd.uniform(0.4, 1.0)) for _ in range(3)]
    ux, uy = math.cos(direction), math.sin(direction)

    def w(x, y, t):
        turn = sum(math.sin(2 * math.pi * (kx * x + ky * y) + ph + 2 * math.pi * f * t) for kx, ky, ph, f in waves)
        heading = direction + swirl * turn / len(waves)
        along = x * ux + y * uy   # gust bands travel downwind
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (along - gust_speed * t) / wavelength)
        s = (speed(t) if callable(speed) else speed) * (1 - gust + 2 * gust * pulse)
        return s * math.cos(heading), s * math.sin(heading)
    return w


def blow(points, field, frames, fps=30, drag=3.0, bounds=None):
    """Carry `points` [(x, y), ...] through `field` (see `wind`) for `frames`
    steps. Each particle's velocity eases towards the local wind at rate
    `drag` per second (higher = lighter, follows the air more tightly).
    `bounds` (x, y, w, h) wraps particles that leave it to the other side.
    Returns one list per frame of `(x, y, vx, vy)` for every particle."""
    dt = 1 / fps
    state = [[x, y, 0.0, 0.0] for x, y in points]
    out = []
    for f in range(frames):
        out.append([tuple(p) for p in state])
        t = f * dt
        k = 1 - math.exp(-drag * dt)
        for p in state:
            wx, wy = field(p[0], p[1], t)
            p[2] += (wx - p[2]) * k
            p[3] += (wy - p[3]) * k
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if bounds:
                bx, by, bw, bh = bounds
                p[0] = bx + (p[0] - bx) % bw
                p[1] = by + (p[1] - by) % bh
    return out


def draw_streaks(cv, particles, color=demo.INK, trail=0.06, width=2.0, alpha=0.9):
    """Draw `(x, y, vx, vy)` particles as streaks pointing back along their
    motion, `trail` seconds long, so faster particles leave longer marks."""
    for x, y, vx, vy in particles:
        cv.line(x - vx * trail, y - vy * trail, x, y, color, width=width, alpha=alpha)


# Demo: a still field of motes; a wind rises from the left, gusts roll
# through in bands and its heading bends up and down across the frame.
COUNT = 520
MARGIN = 60
BOUNDS = (-MARGIN, -MARGIN, demo.W + 2 * MARGIN, demo.H + 2 * MARGIN)
FIELD = wind(direction=0.12, speed=lambda t: 480 * vb.clamp01((t - 0.3) / 1.0), swirl=0.9, gust=0.55,
             wavelength=700, gust_speed=1100, seed=4)


@functools.lru_cache(maxsize=1)
def _frames():
    rnd = random.Random(11)
    pts = [(rnd.uniform(0, demo.W), rnd.uniform(0, demo.H)) for _ in range(COUNT)]
    return blow(pts, FIELD, round(demo.SECONDS * demo.FPS), demo.FPS, drag=2.5, bounds=BOUNDS)


def draw(n, cv):
    t = n / demo.FPS
    # A faint grid of arrows showing the wind itself.
    for gx in range(120, demo.W, 160):
        for gy in range(100, demo.H, 160):
            vx, vy = FIELD(gx, gy, t)
            s = math.hypot(vx, vy)
            if s > 1:
                L = 14 + 30 * min(1.0, s / 700)
                ux, uy = vx / s, vy / s
                cv.line(gx - ux * L / 2, gy - uy * L / 2, gx + ux * L / 2, gy + uy * L / 2, demo.MUTED, width=3,
                        alpha=0.35)
    parts = _frames()[n]
    for i, p in enumerate(parts):
        color = (demo.TEAL, demo.INK, demo.ACCENT)[i % 7 % 3]
        draw_streaks(cv, [p], color=color, trail=0.05, width=2.4)
        if p[2] ** 2 + p[3] ** 2 < 900:
            demo.dot(cv, p[0], p[1], 2.4, color=color)
    cv.mark('particles', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='wind-field',
    name='Wind field',
    family='particles',
    group='Forces',
    aliases=('drag field', 'directional push', 'wind force'),
    definition='Loose particles are swept along by an invisible wind that swings direction and surges '
               'in strength from one spot to the next as it blows.',
    phrasings=('make the dots blow away in gusts of wind',
               'particles drifting sideways like dust caught in a breeze',
               'a wind that picks up and pushes everything across the screen'),
    related=('flow-field', 'curl-noise-flow', 'air-drag', 'streamlines', 'particle-field-repel',
             'particle-morph'),
    api=('videobuilder.capabilities.particles.wind_field.wind',
         'videobuilder.capabilities.particles.wind_field.blow',
         'videobuilder.capabilities.particles.wind_field.draw_streaks'),
    demo=lambda: demo.film(draw),
)

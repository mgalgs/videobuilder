"""Cursor Particle Trail: the same idea as Particle Trail
(`../particles/particle_trail.py`, which keeps the capability) -- a moving
point shedding particles that drift, shrink and fade, here just naming the
moving point a cursor. This module's own code stays (a film may still
import it), but it is no longer a capability of its own."""
import math
import random

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'particle-trail'

# The classic arrow pointer, tip at (0, 0), in px at scale 1.
ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def trail_particles(path, t, rate=120, life=0.9, spread=80, drag=0.15, gravity=70, size=12,
                    colors=(demo.ACCENT,), start=0.0, seed=0):
    """The live particles of a trail shed by `path` at time `t` seconds, as
    `(x, y, r, alpha, color)` tuples, oldest first. `path(t) -> (x, y)` is the
    cursor's position. One particle is born every `1 / rate` s from `start`,
    where the cursor was then; it flies off at a random speed up to `spread`
    px/s, keeps `drag` of the cursor's own velocity (so it streams behind
    rather than sticking), falls `gravity` px/s/s, and shrinks from about
    `size` px radius to nothing over `life` s. Stateless: the same `t` and
    `seed` give the same particles, so frames render in any order."""
    out = []
    dt = 1 / rate
    first = max(math.ceil((start - 1e-9) / dt), math.floor((t - life) / dt) + 1)
    for i in range(first, math.floor(t / dt) + 1):
        born = i * dt
        age = t - born
        if not 0 <= age < life:
            continue
        rnd = random.Random(f'{seed}:{i}')
        x0, y0 = path(born)
        x1, y1 = path(born + 1e-3)
        vx, vy = (x1 - x0) / 1e-3 * drag, (y1 - y0) / 1e-3 * drag
        a, s = rnd.uniform(0, 2 * math.pi), spread * math.sqrt(rnd.random())
        vx, vy = vx + s * math.cos(a), vy + s * math.sin(a)
        k = age / life
        x = x0 + vx * age
        y = y0 + vy * age + 0.5 * gravity * age * age
        r = size * rnd.uniform(0.5, 1.0) * (1 - k)
        out.append((x, y, r, (1 - k) ** 1.5, colors[i % len(colors)]))
    return out


def draw_particle_trail(cv, path, t, glow=True, **kw):
    """Draw the trail `trail_particles(path, t, **kw)` onto `cv`, each spark a
    dot with (when `glow`) a faint halo twice its size. Draw it before the
    cursor so the pointer sits on top."""
    for x, y, r, alpha, color in trail_particles(path, t, **kw):
        if r <= 0.2:
            continue
        if glow:
            cv.sector(x, y, r * 2.2, 0, 2 * math.pi, color, alpha=alpha * 0.18)
        cv.sector(x, y, r, 0, 2 * math.pi, color, alpha=alpha)


def draw_cursor(cv, x, y, scale=1.5, color=demo.INK, edge=demo.BG):
    """An arrow pointer with its tip at (x, y)."""
    pts = [(x + px * scale, y + py * scale) for px, py in ARROW]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    vb.paths.draw(cv, pts, color, fill=True)
    vb.paths.draw(cv, pts, edge, width=2, closed=True)
    cv.mark('cursor', x, y, 21 * scale, 32 * scale)


def _route(t):
    # A lazy figure-of-eight sweep across the frame, slow at the turns.
    x = vb.clamp01((t - 0.2) / 2.6)
    u = (0.5 - 0.5 * math.cos(math.pi * x)) * 2 * math.pi
    return (demo.W / 2 + demo.W * 0.34 * math.cos(u),
            demo.H / 2 + demo.H * 0.24 * math.sin(2 * u))


def draw(n, cv):
    t = n / demo.FPS
    draw_particle_trail(cv, _route, t, colors=(demo.ACCENT, demo.TEAL, demo.INK), start=0.2, seed=3)
    draw_cursor(cv, *_route(t))

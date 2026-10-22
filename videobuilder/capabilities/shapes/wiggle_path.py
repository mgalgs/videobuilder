"""Wiggle Path: a line whose points drift on smooth noise over time, so it
squirms continuously while keeping its overall shape.

`videobuilder.paths.jitter` is the still version (one seeded wobble, the
same every frame); `wiggle` adds time, so the wobble itself moves.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _hash(i, j, seed):
    """A deterministic value in [-1, 1] for lattice point (i, j)."""
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 32767.5 - 1.0


def _noise(u, v, seed, wrap=None):
    """Smooth 2-D value noise in [-1, 1]: `u` along the path, `v` in time.
    `wrap`: the lattice period along `u`, so a closed path meets itself."""
    i, j = math.floor(u), math.floor(v)
    fu, fv = u - i, v - j
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    i0, i1 = (i % wrap, (i + 1) % wrap) if wrap else (i, i + 1)
    a = _hash(i0, j, seed) + (_hash(i1, j, seed) - _hash(i0, j, seed)) * fu
    b = _hash(i0, j + 1, seed) + (_hash(i1, j + 1, seed) - _hash(i0, j + 1, seed)) * fu
    return a + (b - a) * fv


def wiggle(points, t, seed=0, amount=12.0, wavelength=120.0, speed=1.5, step=6.0, closed=False,
           pin_ends=False):
    """`points` at time `t` (seconds) pushed along their normal by smooth
    noise that flows over both the path and time, so drawing it every frame
    with a rising `t` makes the line wiggle. Resampled every ~`step` px first
    so even a two-point line bends. `amount`: px of the largest push.
    `wavelength`: px between bumps along the path. `speed`: how many times a
    second the bumps change. `closed`: an outline (the noise wraps with no
    seam). `pin_ends`: an open path's ends stay put. Deterministic for a
    given `seed` and `t`; `amount=0` returns the resampled path unchanged."""
    pts = list(points)
    total = vb.paths.length(pts, closed)
    if len(pts) < 2 or total == 0:
        return pts
    n = max(3 if closed else 2, round(total / step) + (0 if closed else 1))
    pts = vb.paths.resample(pts, n, closed)
    hop = total / (n if closed else n - 1)
    wrap = max(1, round(total / wavelength)) if closed else None
    scale = (wrap / total) if closed else 1 / wavelength
    v = t * speed
    out = []
    for i, (x, y) in enumerate(pts):
        if closed:
            (px, py), (nx, ny) = pts[i - 1], pts[(i + 1) % n]
        else:
            (px, py), (nx, ny) = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tx, ty = nx - px, ny - py
        d = math.hypot(tx, ty) or 1.0
        u = i * hop * scale
        push = 0.7 * _noise(u, v, seed, wrap) + 0.3 * _noise(u * 2.3, v * 1.7, seed + 1,
                                                            wrap * 2 if wrap else None)
        if pin_ends and not closed:
            push *= math.sin(math.pi * i / (n - 1))
        push *= amount
        out.append((x + ty / d * push, y - tx / d * push))
    return out


def _base():
    """The demo's resting path: a gentle hill across the frame."""
    x0, x1, cy = 110, demo.W - 110, demo.H / 2 + 50
    return [(x0 + (x1 - x0) * k / 40, cy - 130 * math.sin(math.pi * k / 40) ** 2 + 30 * math.sin(k / 3))
            for k in range(41)]


BASE = _base()


def draw(n, cv):
    t = n / demo.FPS
    vb.paths.draw(cv, BASE, demo.MUTED, width=2, alpha=0.35)   # the shape it keeps
    pts = wiggle(BASE, t, seed=3, amount=22, wavelength=70, speed=2.5, step=4)
    vb.paths.draw(cv, pts, demo.ACCENT, width=5)
    for x, y in (pts[0], pts[-1]):
        demo.dot(cv, x, y, r=7, color=demo.ACCENT)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv.mark('path', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='wiggle-path',
    name='Wiggle path',
    family='shapes',
    group='Lines & strokes',
    aliases=('jitter path', 'noisy path', 'path noise', 'wiggle stroke'),
    definition='A drawn line keeps squirming as its points drift on smooth, ever-changing noise, '
               'while its overall shape stays the same.',
    phrasings=('make the line wobble around like it is alive',
               'a squiggly stroke that keeps wiggling but holds its shape',
               'add some organic noise to the path so it never sits still'),
    related=('jiggle', 'noise-vertex-wobble', 'scanline-jitter', 'wobble', 'path-emitter', 'tape-wobble'),
    api=('videobuilder.capabilities.shapes.wiggle_path.wiggle', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)

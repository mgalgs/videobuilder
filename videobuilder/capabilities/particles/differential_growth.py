"""Differential Growth: a closed loop of linked points that keeps lengthening
while its points push each other apart, so the line buckles into ever finer
meandering folds, like coral, brain tissue or a crumpled ribbon."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _grid(points, cell):
    g = {}
    for i, (x, y) in enumerate(points):
        g.setdefault((int(x // cell), int(y // cell)), []).append(i)
    return g


def differential_growth(points, steps, spacing=6.0, radius=None, bounds=None, seed=0, max_points=1400,
                        every=1):
    """Grow the closed point list `points` for `steps` simulation steps and
    return a list of `steps + 1` snapshots (the input first), each a list of
    (x, y) tuples to draw closed.

    Each step: every point moves toward the midpoint of its two neighbours
    (keeps the line smooth), away from any other point nearer than `radius`
    (default `3 * spacing`, so the line never crosses itself), and gets a tiny
    seeded nudge; then any link longer than `spacing` is split in two, so the
    loop keeps lengthening until it holds `max_points`. `bounds`, an optional
    `(cx, cy, r)` circle, keeps the growth inside it. Only every `every`-th
    step is kept in the result, so `steps` should be a multiple of it."""
    rnd = random.Random(seed)
    radius = radius or 3.0 * spacing
    pts = [tuple(p) for p in points]
    out = [pts]
    r2 = radius * radius
    for step in range(1, steps + 1):
        n = len(pts)
        grid = _grid(pts, radius)
        moved = []
        for i, (x, y) in enumerate(pts):
            (ax, ay), (bx, by) = pts[i - 1], pts[(i + 1) % n]
            dx = ((ax + bx) / 2 - x) * 0.45
            dy = ((ay + by) / 2 - y) * 0.45
            gx, gy = int(x // radius), int(y // radius)
            px = py = 0.0
            for cx in (gx - 1, gx, gx + 1):
                for cy in (gy - 1, gy, gy + 1):
                    for j in grid.get((cx, cy), ()):
                        if j == i:
                            continue
                        ox, oy = x - pts[j][0], y - pts[j][1]
                        d2 = ox * ox + oy * oy
                        if 0 < d2 < r2:
                            d = math.sqrt(d2)
                            f = (radius - d) / radius
                            px += ox / d * f
                            py += oy / d * f
            dx += px * 0.9 + rnd.uniform(-0.15, 0.15)
            dy += py * 0.9 + rnd.uniform(-0.15, 0.15)
            nx, ny = x + dx, y + dy
            if bounds:
                bcx, bcy, br = bounds
                ex, ey = nx - bcx, ny - bcy
                e = math.hypot(ex, ey)
                if e > br:
                    nx, ny = bcx + ex / e * br, bcy + ey / e * br
            moved.append((nx, ny))
        pts = []
        for i, a in enumerate(moved):
            pts.append(a)
            b = moved[(i + 1) % len(moved)]
            if len(moved) + len(pts) - i - 1 < max_points and math.dist(a, b) > spacing:
                pts.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        if step % every == 0:
            out.append(pts)
    return out


def draw_differential_growth(cv, points, color, width=2.5, fill=None, fill_alpha=0.18):
    """Draw one snapshot from `differential_growth` as a closed line `width`
    px wide, over an optional translucent `fill` of its inside."""
    if fill:
        vb.paths.draw(cv, points, fill, fill=True, alpha=fill_alpha)
    vb.paths.draw(cv, points, color, width=width, closed=True)


START, END = 0.3, 2.7
SUB = 4  # simulation steps per frame


@functools.lru_cache(maxsize=1)
def _frames():
    cx, cy = demo.W / 2, demo.H / 2
    seed_loop = [(cx + 40 * math.cos(a), cy + 40 * math.sin(a))
                 for a in (2 * math.pi * k / 40 for k in range(40))]
    frames = round((END - START) * demo.FPS)
    return differential_growth(seed_loop, frames * SUB, spacing=5.0, bounds=(cx, cy, 240), seed=7,
                               max_points=2000, every=SUB)


def draw(n, cv):
    snaps = _frames()
    k = min(len(snaps) - 1, max(0, round((n / demo.FPS - START) * demo.FPS)))
    pts = snaps[k]
    draw_differential_growth(cv, pts, demo.ACCENT, width=2.2, fill=demo.ACCENT)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('growth', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='differential-growth',
    name='Differential growth',
    family='particles',
    group='Reaction & growth',
    aliases=('differential line growth', 'growing line', 'organic folding growth'),
    definition='A closed line that keeps getting longer while its points shove each other away, '
               'so it wrinkles into tighter and tighter winding folds like coral or a brain.',
    phrasings=('a loop that grows and crinkles up like coral',
               'an organic line that keeps folding in on itself as it spreads',
               'brain-like squiggles growing out from a small circle'),
    related=('koch-snowflake', 'decision-tree-branch-growth', 'bar-grow', 'stacked-bar-build',
             'offset-path-expansion', 'lenia'),
    api=('videobuilder.techniques.particles.differential_growth.differential_growth',
         'videobuilder.techniques.particles.differential_growth.draw_differential_growth'),
    demo=lambda: demo.film(draw),
)

"""Diffusion-limited aggregation: particles wander at random until they touch
a growing cluster and freeze there, so the cluster grows as branching,
coral-like fingers -- the tips catch the wanderers before they reach inside."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
_NEAR = tuple((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


@functools.lru_cache(maxsize=8)
def dla_cluster(count=1500, seed=1):
    """Grow a diffusion-limited aggregate on a square lattice from one seed
    cell at (0, 0). Returns a tuple of `count` (x, y, parent) in stick order:
    lattice cell `(x, y)` and the index of the cell it stuck to (-1 for the
    seed). Deterministic for a given `seed`; cached, so a film can call it
    every frame and draw a growing prefix (see `draw_dla`)."""
    rng = random.Random(seed)
    cells = [(0, 0, -1)]
    index = {(0, 0): 0}
    reach = 0.0  # radius of the cluster so far
    while len(cells) < count:
        launch = reach + 5
        a = rng.random() * math.tau
        x, y = round(launch * math.cos(a)), round(launch * math.sin(a))
        while True:
            d = math.hypot(x, y)
            if d > 3 * launch + 20:  # wandered off: launch again from the circle
                a = rng.random() * math.tau
                x, y = round(launch * math.cos(a)), round(launch * math.sin(a))
                continue
            if d > reach + 4:  # far from the cluster: one long jump, same random walk statistically
                a, j = rng.random() * math.tau, d - reach - 3
                x, y = x + round(j * math.cos(a)), y + round(j * math.sin(a))
                continue
            hit = next((index[(x + dx, y + dy)] for dx, dy in _NEAR if (x + dx, y + dy) in index), None)
            if hit is not None and (x, y) not in index:
                index[(x, y)] = len(cells)
                cells.append((x, y, hit))
                reach = max(reach, d)
                break
            dx, dy = _STEPS[rng.randrange(4)]
            x, y = x + dx, y + dy
    return tuple(cells)


def draw_dla(cv, cluster, cx, cy, cell, upto=None, color=demo.INK, tip=demo.ACCENT, width=None, fresh=60):
    """Draw the first `upto` cells of `cluster` (from `dla_cluster`) centred at
    (cx, cy), `cell` px per lattice step: each cell joined to the one it stuck
    to. The newest `fresh` cells are drawn in `tip`, so the growing ends
    read as live."""
    n, c = len(cluster) if upto is None else max(1, min(len(cluster), int(upto))), cv.ctx
    c.set_line_width(width or cell * 0.8)
    c.set_line_cap(1)  # round
    split = max(1, n - fresh)
    for lo, hi, col in ((1, split, color), (split, n, tip)):
        c.new_path()
        for x, y, parent in cluster[lo:hi]:
            px, py, _ = cluster[parent]
            c.move_to(cx + px * cell, cy + py * cell)
            c.line_to(cx + x * cell, cy + y * cell)
        c.set_source_rgba(*vb.canvas.rgba(col))
        c.stroke()
    demo.dot(cv, cx, cy, cell * 1.3, tip)


def _walkers(n, count=160, inner=60, outer=430, seed=7):
    """Positions of `count` drifting particles at frame `n`: each a seeded
    random walk confined to a ring around the centre."""
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        a, r = rng.random() * math.tau, inner + (outer - inner) * math.sqrt(rng.random())
        x, y = r * math.cos(a), r * math.sin(a)
        step = random.Random(rng.random())
        for _ in range(n):
            x, y = x + step.gauss(0, 4), y + step.gauss(0, 4)
            d = math.hypot(x, y)
            if d > outer or d < inner:
                f = (outer if d > outer else inner) / d
                x, y = x * f, y * f
        out.append((x, y))
    return out


def draw(n, cv):
    cluster = dla_cluster(1800, seed=3)
    full = max(math.hypot(x, y) for x, y, _ in cluster)
    cx, cy, cell = demo.W / 2, demo.H / 2, 0.44 * demo.H / full
    p = demo.phase(n, 0.2, 2.7)
    upto = 1 + (len(cluster) - 1) * p ** 1.3
    reach = max(math.hypot(x, y) for x, y, _ in cluster[:max(1, int(upto))]) * cell
    for x, y in _walkers(n, inner=reach + 30, outer=reach + 200):
        demo.dot(cv, cx + x, cy + y, 3.2, demo.MUTED, alpha=0.6)
    draw_dla(cv, cluster, cx, cy, cell, upto)
    cv.mark('cluster', cx - reach, cy - reach, 2 * reach, 2 * reach)


CAPABILITY = Capability(
    id='diffusion-limited-aggregation',
    name='Diffusion-limited aggregation',
    family='particles',
    group='Reaction & growth',
    aliases=('DLA', 'Brownian tree'),
    definition='Drifting particles freeze the moment they bump into a growing clump, '
               'which spreads outward as a branching, frost-like fractal.',
    phrasings=('grow a branching crystal out of wandering dots',
               'frost or coral spreading out from a single point',
               'particles drift around and stick together into a fractal tree'),
    related=('recursive-tree', 'random-walk', 'recursive-rectangle-subdivision', 'physarum-slime-mold',
             'fractal-brownian-motion', 'circle-packing'),
    api=('videobuilder.capabilities.particles.diffusion_limited_aggregation.dla_cluster',
         'videobuilder.capabilities.particles.diffusion_limited_aggregation.draw_dla'),
    demo=lambda: demo.film(draw),
)

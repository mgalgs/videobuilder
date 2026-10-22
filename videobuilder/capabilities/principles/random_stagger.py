"""Random Stagger: a group of items each starts its own entrance after a
random delay, so the set fills in scattered rather than in a readable order."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def random_delays(count, seed=0):
    """`count` start times in [0, 1], one per item, in random order. They are
    stretched so the earliest is exactly 0 and the latest exactly 1 (with one
    item, 0), so the group always uses the whole window. The same `seed` gives
    the same delays."""
    rng = random.Random(seed)
    raw = [rng.random() for _ in range(count)]
    lo, hi = min(raw, default=0), max(raw, default=0)
    return [(r - lo) / (hi - lo) if hi > lo else 0.0 for r in raw]


def random_stagger(count, p, duration=0.3, seed=0, ease=vb.clamp01):
    """Per-item progress for `count` items at overall progress `p` (0 -> 1).
    Each item runs its own 0 -> 1 over `duration` (a fraction of the whole),
    starting at a random delay from `random_delays`; the first starts at
    `p` = 0 and the last finishes at `p` = 1. `ease` shapes each item's own
    move. Returns a list of floats, item order unchanged."""
    duration = min(max(duration, 1e-6), 1.0)
    return [ease(vb.clamp01((p - d * (1 - duration)) / duration)) for d in random_delays(count, seed)]


ROWS = COLS = 5
CELL, GAP = 70, 16


def draw(n, cv):
    size = COLS * CELL + (COLS - 1) * GAP
    x0, y0 = (demo.W - size) / 2, (demo.H - size) / 2
    tiles = random_stagger(ROWS * COLS, demo.phase(n, 0.3, 2.5), duration=0.22, seed=11)
    for i, q in enumerate(tiles):
        x, y = x0 + (i % COLS) * (CELL + GAP), y0 + (i // COLS) * (CELL + GAP)
        cv.outline(x, y, CELL, CELL, demo.LINE, width=2, radius=14, alpha=0.6)  # the empty slot
        if q <= 0:
            continue
        s = 0.4 + 0.6 * vb.ease_out_back(q)
        w = CELL * s
        cv.rect(x + (CELL - w) / 2, y + (CELL - w) / 2, w, w, demo.ACCENT, radius=14 * s,
                alpha=vb.clamp01(q * 3))
    cv.mark('grid', x0, y0, size, size)


TECHNIQUE = Technique(
    id='random-stagger',
    name='Random Stagger',
    family='principles',
    group='Stagger',
    aliases=('random delay', 'jittered stagger', 'scatter timing', 'random order stagger'),
    definition='Every item in a group begins its entrance after its own random delay, '
               'so the set fills in scattered with no visible order.',
    phrasings=('have the tiles pop in at random instead of one after another',
               'bring the items in at scattered times so it looks less mechanical',
               'stagger them but shuffle the order'),
    related=('random-order-character-reveal', 'offset', 'linear-repeater-stagger', 'staggered-cascade-reveal',
             'letter-sort-animation', 'wiggle-path'),
    api=('videobuilder.techniques.principles.random_stagger.random_stagger',
         'videobuilder.techniques.principles.random_stagger.random_delays'),
    demo=lambda: demo.film(draw),
)

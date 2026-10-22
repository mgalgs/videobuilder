"""Brian's Brain: a three-state cellular automaton. A resting cell fires when
exactly two of its eight neighbours are firing; a firing cell turns dying for
one step, then rests again. A random clump bursts outward and breaks up into
small sparks that crawl away across the grid."""
import functools
import random

from .. import _demo as demo
from ..schema import Capability

NEIGHBOURS = tuple((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


def brain_step(firing, dying, cols, rows):
    """One generation: `firing` and `dying` are sets of `(col, row)` cells on
    a `cols` x `rows` grid (the edge is dead, so sparks leave the frame).
    Returns the next `(firing, dying)`."""
    counts = {}
    for cx, cy in firing:
        for dx, dy in NEIGHBOURS:
            c = (cx + dx, cy + dy)
            counts[c] = counts.get(c, 0) + 1
    born = {c for c, k in counts.items()
            if k == 2 and c not in firing and c not in dying and 0 <= c[0] < cols and 0 <= c[1] < rows}
    return born, set(firing)


def seed_clump(cols, rows, radius, density=0.35, seed=0, center=None):
    """A random disc of firing cells, `radius` cells across, centred on the
    grid (or at `center`); `density` is the share of cells lit."""
    rnd = random.Random(seed)
    cx, cy = center or (cols // 2, rows // 2)
    return {(x, y) for x in range(cx - radius, cx + radius + 1) for y in range(cy - radius, cy + radius + 1)
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius and rnd.random() < density}


def generations(firing, cols, rows, steps):
    """The run from `firing` (all dying empty): a tuple of `steps + 1`
    `(firing, dying)` pairs, generation 0 first. Compute once and index by
    frame; each step depends on the one before."""
    out, dying = [(frozenset(firing), frozenset())], set()
    firing = set(firing)
    for _ in range(steps):
        firing, dying = brain_step(firing, dying, cols, rows)
        out.append((frozenset(firing), frozenset(dying)))
    return tuple(out)


def draw_brain(cv, firing, dying, x, y, cell, fire=demo.INK, glow=demo.ACCENT, fade=demo.TEAL):
    """Draw one generation with its grid's top-left at (x, y), `cell` pixels
    per cell: firing cells bright with a soft `glow` halo, dying cells a dim
    `fade` afterimage. Resting cells draw nothing."""
    for cx, cy in dying:
        cv.rect(x + cx * cell + 1, y + cy * cell + 1, cell - 2, cell - 2, fade, radius=cell * 0.2, alpha=0.45)
    for cx, cy in firing:
        cv.rect(x + cx * cell - cell * 0.6, y + cy * cell - cell * 0.6, cell * 2.2, cell * 2.2, glow,
                radius=cell, alpha=0.3)
    for cx, cy in firing:
        cv.rect(x + cx * cell + 1, y + cy * cell + 1, cell - 2, cell - 2, fire, radius=cell * 0.2)


CELL = 10
COLS, ROWS = demo.W // CELL, demo.H // CELL
RATE = 12  # generations per second


@functools.lru_cache(maxsize=1)
def _run():
    return generations(seed_clump(COLS, ROWS, 8, density=0.5, seed=1), COLS, ROWS,
                       int(demo.SECONDS * RATE) + 1)


def draw(n, cv):
    run = _run()
    firing, dying = run[min(len(run) - 1, int(n / demo.FPS * RATE))]
    draw_brain(cv, firing, dying, (demo.W - COLS * CELL) / 2, (demo.H - ROWS * CELL) / 2, CELL)


CAPABILITY = Capability(
    id='brian-s-brain',
    name="Brian's Brain",
    family='particles',
    group='Cellular automata',
    aliases=('three-state automaton', 'brians brain automaton'),
    definition='A grid of cells that flash on, fade for one beat and go dark, so a seeded clump '
               'bursts into flickering sparks that scatter outward across the frame.',
    phrasings=('a cellular automaton where blinking cells spread out in waves',
               'little glowing pixel sparks that break off a cluster and crawl away',
               'a generative grid of firing cells with a fading trail behind each one'),
    related=('reaction-diffusion', 'rossler-attractor', 'outline-pulse-glow', 'fireflies', 'lorenz-attractor',
             'kuramoto-synchronization'),
    api=('videobuilder.capabilities.particles.brian_s_brain.draw_brain',
         'videobuilder.capabilities.particles.brian_s_brain.generations',
         'videobuilder.capabilities.particles.brian_s_brain.brain_step',
         'videobuilder.capabilities.particles.brian_s_brain.seed_clump'),
    demo=lambda: demo.film(draw),
)

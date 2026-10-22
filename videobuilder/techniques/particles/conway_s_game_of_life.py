"""Conway's Game of Life: a grid of square cells that live or die each step
by counting their neighbours, so a random scatter churns into blinking,
gliding and settling patterns."""
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLIDER = ((1, 0), (2, 1), (0, 2), (1, 2), (2, 2))


def life_step(cells, cols, rows, wrap=True):
    """One generation of the standard rule (B3/S23) on a `cols` x `rows`
    grid. `cells` is a set of live `(x, y)`; returns the next set. With
    `wrap` the edges join up (a torus); without it, cells off the grid are
    dead."""
    counts = {}
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    nx, ny = x + dx, y + dy
                    if wrap:
                        nx, ny = nx % cols, ny % rows
                    elif not (0 <= nx < cols and 0 <= ny < rows):
                        continue
                    counts[nx, ny] = counts.get((nx, ny), 0) + 1
    return {c for c, k in counts.items() if k == 3 or (k == 2 and c in cells)}


def life_generations(cells, cols, rows, steps, wrap=True):
    """The seed and the next `steps` generations, as a tuple of frozensets."""
    out = [frozenset(cells)]
    for _ in range(steps):
        out.append(frozenset(life_step(out[-1], cols, rows, wrap)))
    return tuple(out)


def random_soup(cols, rows, density=0.35, seed=0, box=None):
    """A random seed: each cell of `box` (`(x, y, w, h)` in cells, default
    the whole grid) is alive with probability `density`."""
    rng = random.Random(seed)
    x0, y0, w, h = box or (0, 0, cols, rows)
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h) if rng.random() < density}


def draw_life(cv, generations, t, x, y, cell, color, cols, rows, grid=None, gap=2, radius=3):
    """Draw the grid at time `t`, measured in generations (2.5 is halfway
    from generation 2 to 3), with its top-left at (x, y), `cell` px per
    cell on a `cols` x `rows` grid. Cells born in the step fade in and cells
    dying fade out, so the churn reads smoothly at any step rate. `grid` draws faint lines between
    cells in that colour."""
    t = max(0.0, min(t, len(generations) - 1))
    i = int(t)
    a, b = generations[i], generations[min(i + 1, len(generations) - 1)]
    p = vb.clamp01((t - i) * 2.5)  # change happens early in the step, then holds
    if grid:
        for k in range(cols + 1):
            cv.line(x + k * cell, y, x + k * cell, y + rows * cell, grid, width=1)
        for k in range(rows + 1):
            cv.line(x, y + k * cell, x + cols * cell, y + k * cell, grid, width=1)
    s = cell - 2 * gap
    for cx, cy in a | b:
        alpha = 1.0 if (cx, cy) in a and (cx, cy) in b else (p if (cx, cy) in b else 1 - p)
        if alpha > 0.01:
            cv.rect(x + cx * cell + gap, y + cy * cell + gap, s, s, color, radius=radius, alpha=alpha)


COLS, ROWS, CELL = 48, 27, 20
STEPS_PER_SECOND = 10


@lru_cache(maxsize=1)
def _demo_generations():
    cells = random_soup(COLS, ROWS, density=0.38, seed=11, box=(14, 6, 20, 15))
    for gx, gy in ((3, 3), (40, 19)):
        cells |= {(gx + dx, gy + dy) for dx, dy in GLIDER}
    return life_generations(cells, COLS, ROWS, int(demo.SECONDS * STEPS_PER_SECOND) + 1)


def draw(n, cv):
    t = max(0.0, n / demo.FPS - 0.4) * STEPS_PER_SECOND  # hold the seed briefly, then run
    draw_life(cv, _demo_generations(), t, 0, 0, CELL, demo.TEAL, COLS, ROWS, grid=demo.LINE)
    cv.mark('grid', 0, 0, COLS * CELL, ROWS * CELL)


TECHNIQUE = Technique(
    id='conway-s-game-of-life',
    name="Conway's Game of Life",
    family='particles',
    group='Cellular automata',
    aliases=('game of life', 'life automaton', 'cellular automaton', 'B3/S23'),
    definition='Square cells on a grid switch on and off each step according to how many of their '
               'neighbours are lit, so a random scatter boils into blinking, drifting, settling patterns.',
    phrasings=('a grid of pixels that breed and die like the classic life simulation',
               'cells that multiply and die off step by step on a grid',
               'a cellular automaton background with little gliders moving across'),
    related=('eden-growth', 'particle-life', 'voronoi-cells', 'infinite-perspective-grid',
             'voronoi-relaxation', 'smoke-simulation'),
    api=('videobuilder.techniques.particles.conway_s_game_of_life.draw_life',
         'videobuilder.techniques.particles.conway_s_game_of_life.life_generations',
         'videobuilder.techniques.particles.conway_s_game_of_life.life_step',
         'videobuilder.techniques.particles.conway_s_game_of_life.random_soup'),
    demo=lambda: demo.film(draw),
)

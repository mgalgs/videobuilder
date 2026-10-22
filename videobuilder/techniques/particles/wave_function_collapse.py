"""Wave function collapse: every cell of a grid starts able to be any tile;
one at a time the most-constrained cell picks a tile, and the choice ripples
out to its neighbours, ruling out tiles whose edges would not meet, until a
pattern with no broken joins fills the grid."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# A tile is its four edge sockets (north, east, south, west); two tiles may sit
# side by side when the sockets on their shared edge are equal.
N, E, S, W = range(4)
STEPS = ((-1, 0), (0, 1), (1, 0), (0, -1))   # (drow, dcol) towards N, E, S, W

# Pipe tiles: every way of joining 0, 2, 3 or 4 edges (no dead ends), so the
# pipes the collapse lays down always close up into loops and runs.
PIPE_TILES = tuple(t for t in ((n, e, s, w) for n in (0, 1) for e in (0, 1) for s in (0, 1) for w in (0, 1))
                   if sum(t) != 1)
PIPE_WEIGHTS = tuple({0: 3.0, 2: 2.0, 3: 0.35, 4: 0.15}[sum(t)] for t in PIPE_TILES)


def wave_function_collapse(rows, cols, tiles=PIPE_TILES, weights=None, seed=0, wander=0.0, tries=20):
    """Collapse a `rows` x `cols` grid of `tiles` (4-tuples of edge sockets,
    N E S W). Returns `(steps, options)`: `steps[k]` is the k-th collapse as
    `(row, col, tile_index)`, and `options[k]` is, before that collapse, how
    many tiles each cell (row-major) could still be -- `options[-1]` is the
    finished grid, all ones. Each step collapses a cell with the fewest
    options left (ties broken at random), picks one of them by `weights`,
    then propagates; with chance `wander` (0..1) it collapses any open cell
    instead, so the pattern grows from scattered spots, not one front. A contradiction restarts with the next seed, up to
    `tries` times. The same arguments give the same result."""
    weights = weights or [1.0] * len(tiles)
    fits = [[{j for j, b in enumerate(tiles) if a[d] == b[(d + 2) % 4]} for d in range(4)] for a in tiles]
    for attempt in range(tries):
        result = _attempt(rows, cols, len(tiles), weights, fits, wander, random.Random(f'{seed}:{attempt}'))
        if result:
            return result
    raise ValueError(f'wave_function_collapse: no consistent {rows}x{cols} grid in {tries} tries')


def _attempt(rows, cols, count, weights, fits, wander, rng):
    cells = [set(range(count)) for _ in range(rows * cols)]
    steps, options = [], []
    while True:
        sizes = tuple(len(c) for c in cells)
        open_ = [i for i, k in enumerate(sizes) if k > 1]
        if not open_:
            options.append(sizes)
            return steps, options
        least = min(sizes[i] for i in open_)
        i = rng.choice(open_ if rng.random() < wander else [i for i in open_ if sizes[i] == least])
        choice = sorted(cells[i])
        pick = rng.choices(choice, [weights[j] for j in choice])[0]
        options.append(sizes)
        steps.append((i // cols, i % cols, pick))
        cells[i] = {pick}
        stack = [i]
        while stack:
            at = stack.pop()
            r, c = divmod(at, cols)
            for d, (dr, dc) in enumerate(STEPS):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < rows and 0 <= cc < cols):
                    continue
                nb = rr * cols + cc
                allowed = set().union(*(fits[t][d] for t in cells[at]))
                if not cells[nb] <= allowed:
                    cells[nb] &= allowed
                    if not cells[nb]:
                        return None
                    stack.append(nb)


def draw_pipe(cv, x, y, size, tile, color, width=6, alpha=1.0):
    """Draw pipe `tile` (N E S W sockets) in the cell at (x, y): a turn
    between two neighbouring edges is a quarter arc, any other join runs
    straight through the centre."""
    cx, cy, h = x + size / 2, y + size / 2, size / 2
    on = [d for d in range(4) if tile[d]]
    if len(on) == 2 and (on[1] - on[0]) % 2:
        a, b = on
        if (a, b) == (N, W):
            a, b = W, N
        # the corner shared by edges a and b, and the arc sweep from a's side to b's
        corner = {(N, E): (x + size, y), (E, S): (x + size, y + size), (S, W): (x, y + size), (W, N): (x, y)}
        start = {(N, E): math.pi / 2, (E, S): math.pi, (S, W): 3 * math.pi / 2, (W, N): 0}[(a, b)]
        cv.arc(*corner[(a, b)], h, start, start + math.pi / 2, color, width=width, alpha=alpha)
        return
    for d in on:
        dr, dc = STEPS[d]
        cv.line(cx, cy, cx + dc * h, cy + dr * h, color, width=width, alpha=alpha)
    if on:
        cv.sector(cx, cy, width / 2, 0, 2 * math.pi, color, alpha=alpha)


ROWS, COLS, SIZE = 8, 14, 52


@functools.lru_cache(maxsize=1)
def _solved():
    return wave_function_collapse(ROWS, COLS, PIPE_TILES, PIPE_WEIGHTS, seed=3, wander=0.12)


def draw(n, cv):
    steps, options = _solved()
    t0, t1 = 0.35, 2.55
    # how many collapses have happened, as a float so the newest tile can fade in
    k = vb.clamp01((n / demo.FPS - t0) / (t1 - t0)) * len(steps)
    done = int(k)
    sizes = options[done]
    x0, y0 = (demo.W - COLS * SIZE) / 2, (demo.H - ROWS * SIZE) / 2
    most = len(PIPE_TILES)
    for r in range(ROWS + 1):
        cv.line(x0, y0 + r * SIZE, x0 + COLS * SIZE, y0 + r * SIZE, demo.LINE, width=1)
    for c in range(COLS + 1):
        cv.line(x0 + c * SIZE, y0, x0 + c * SIZE, y0 + ROWS * SIZE, demo.LINE, width=1)
    # undecided cells: a dot per remaining option, so the superposition visibly shrinks
    for i, left in enumerate(sizes):
        if left <= 1:
            continue
        r, c = divmod(i, COLS)
        for j in range(left):
            dx, dy = j % 4, j // 4
            cv.sector(x0 + c * SIZE + 14 + dx * 8, y0 + r * SIZE + 14 + dy * 8, 1.8, 0, 2 * math.pi,
                      demo.MUTED, alpha=0.25 + 0.35 * (1 - left / most))
    recent = 6   # the last few collapses glow in the accent colour, then settle to teal
    for s, (r, c, tile) in enumerate(steps[:done + 1]):
        age = k - s
        if age <= 0:
            continue
        x, y = x0 + c * SIZE, y0 + r * SIZE
        fresh = vb.clamp01(1 - (age - 1) / recent)
        if fresh > 0:
            cv.rect(x + 2, y + 2, SIZE - 4, SIZE - 4, demo.ACCENT, radius=6, alpha=0.22 * fresh)
        draw_pipe(cv, x, y, SIZE, PIPE_TILES[tile], demo.TEAL, width=6, alpha=min(1.0, age))
        if fresh > 0:
            draw_pipe(cv, x, y, SIZE, PIPE_TILES[tile], demo.ACCENT, width=6, alpha=min(1.0, age) * fresh)
    cv.mark('grid', x0, y0, COLS * SIZE, ROWS * SIZE)


TECHNIQUE = Technique(
    id='wave-function-collapse',
    name='Wave function collapse',
    family='particles',
    group='Tiling & patterns',
    aliases=('WFC', 'constraint tiling', 'constraint-based tile generation'),
    definition='A grid of undecided cells settles one cell at a time, each pick narrowing what its '
               'neighbours may become, until a seamless tiled pattern covers the whole grid.',
    phrasings=('fill the grid with tiles that pick themselves one by one and always connect up',
               'a procedural pattern that grows cell by cell as the options narrow down',
               'show a maze of pipes solving itself tile by tile'),
    related=('scale-tile-wave', 'pattern-tiling', 'grid-wave-loader', 'bento-grid-reveal',
             'grid-diagonal-stagger', 'tile-flip'),
    api=('videobuilder.techniques.particles.wave_function_collapse.wave_function_collapse',
         'videobuilder.techniques.particles.wave_function_collapse.draw_pipe',
         'videobuilder.techniques.particles.wave_function_collapse.PIPE_TILES'),
    demo=lambda: demo.film(draw),
)

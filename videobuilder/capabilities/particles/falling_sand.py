"""Falling sand: a grid of cells where each grain drops into the empty cell
below it, or slides diagonally down when that is blocked, so a poured stream
heaps into slopes that spill over edges onto whatever lies beneath."""
import random

from .. import _demo as demo
from ..schema import Technique

SAND = ('#e9b62f', '#d8a222', '#f3cb52')


class SandGrid:
    """A `cols` x `rows` cellular sand box. Cells are empty, wall or grain;
    each `step()` moves every grain at most one cell: straight down if that
    cell is free, otherwise diagonally down-left or down-right (picked at
    random when both are free). Grains stop on walls, other grains and the
    bottom row. The same `seed` gives the same run."""

    def __init__(self, cols, rows, seed=0):
        self.cols, self.rows = cols, rows
        self.cells = [bytearray(cols) for _ in range(rows)]  # 0 empty, 1 wall, 2+ grain (2 + shade)
        self.grains = []                                     # [row, col, shade]
        self.rng = random.Random(seed)

    def wall(self, c0, r0, c1, r1):
        """Make the cells from (c0, r0) to (c1, r1) inclusive solid."""
        for r in range(max(0, r0), min(self.rows, r1 + 1)):
            for c in range(max(0, c0), min(self.cols, c1 + 1)):
                self.cells[r][c] = 1

    def drop(self, col, row=0, shade=None):
        """Put a grain at (col, row) if that cell is empty. `shade` indexes
        the palette `draw` is given (random of three when None)."""
        if 0 <= col < self.cols and 0 <= row < self.rows and not self.cells[row][col]:
            shade = self.rng.randrange(3) if shade is None else shade
            self.cells[row][col] = 2 + shade
            self.grains.append([row, col, shade])

    def pour(self, col, rate=2, spread=1):
        """Drop up to `rate` grains on the top row within `spread` cells of `col`."""
        for _ in range(rate):
            self.drop(col + self.rng.randint(-spread, spread))

    def _free(self, r, c):
        return 0 <= c < self.cols and r < self.rows and not self.cells[r][c]

    def step(self):
        """Advance every grain one update, lowest first so a column falls together."""
        cells, rng = self.cells, self.rng
        self.grains.sort(key=lambda g: (-g[0], rng.random()))
        for g in self.grains:
            r, c, _ = g
            if r + 1 >= self.rows:
                continue
            if self._free(r + 1, c):
                nc = c
            else:
                sides = [d for d in (-1, 1) if self._free(r + 1, c + d) and self._free(r, c + d)]
                if not sides:
                    continue
                nc = c + rng.choice(sides)
            cells[r + 1][nc], cells[r][c] = cells[r][c], 0
            g[0], g[1] = r + 1, nc

    def snapshot(self):
        """The grains now, as `(row, col, shade)` tuples."""
        return tuple(tuple(g) for g in self.grains)


def draw_sand(cv, grains, x, y, cell, colors=SAND):
    """Draw a `snapshot()` with the grid's top-left at (x, y), each cell
    `cell` pixels square, grain colour `colors[shade % len(colors)]`."""
    for r, c, shade in grains:
        cv.rect(x + c * cell, y + r * cell, cell, cell, colors[shade % len(colors)])


def simulate(grid, frames, steps=3, emit=None):
    """Run `grid` for `frames` frames of `steps` updates each, calling
    `emit(grid, frame)` before each frame's updates (to pour, say). Returns
    one `snapshot()` per frame, so a film's `draw(n, cv)` can index it."""
    out = []
    for n in range(frames):
        for _ in range(steps):
            if emit:
                emit(grid, n)
            grid.step()
        out.append(grid.snapshot())
    return out


CELL = 5
COLS, ROWS = demo.W // CELL, demo.H // CELL   # 192 x 108
LEDGE = (60, 52, 100, 53)                     # c0, r0, c1, r1
FLOOR = ROWS - 10


def _run():
    g = SandGrid(COLS, ROWS, seed=3)
    g.wall(*LEDGE)
    g.wall(16, FLOOR, COLS - 17, FLOOR + 1)

    def emit(grid, n):
        if n < 70:
            grid.pour(90 if n < 40 else 90 + int((n - 40) * 1.2), rate=2)
    return simulate(g, round(demo.SECONDS * demo.FPS), steps=4, emit=emit)


def _demo():
    frames = []

    def draw(n, cv):
        if not frames:
            frames.extend(_run())
        c0, r0, c1, r1 = LEDGE
        cv.rect(c0 * CELL, r0 * CELL, (c1 - c0 + 1) * CELL, (r1 - r0 + 1) * CELL, demo.MUTED)
        demo.floor(cv, FLOOR * CELL + 2)
        draw_sand(cv, frames[n], 0, 0, CELL)
        cv.mark('sand', 0, 0, demo.W, demo.H)
    return demo.film(draw)


TECHNIQUE = Technique(
    id='falling-sand',
    name='Falling sand',
    family='particles',
    group='Cellular automata',
    aliases=('powder simulation', 'sand automaton', 'sand sim'),
    definition='Grains on a pixel grid drop one cell at a time and slide diagonally off anything below, '
               'so a pouring stream builds into sloped heaps that overflow ledges.',
    phrasings=('pour pixel sand that piles up and spills off the edge',
               'a sand simulation where the grains stack into little dunes',
               'grains trickle down and heap up like in a falling-sand game'),
    related=('sandpile-avalanche', 'rigid-body-pile', 'ball-bounce', 'shape-stacking-drop',
             'physics-letter-drop', 'dust-motes'),
    api=('videobuilder.techniques.particles.falling_sand.SandGrid',
         'videobuilder.techniques.particles.falling_sand.simulate',
         'videobuilder.techniques.particles.falling_sand.draw_sand'),
    demo=_demo,
)

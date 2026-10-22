"""Rule 30 automaton: a single live cell at the top of a grid, and each new row
below worked out from the three cells above it, so a chaotic triangle of
nested shapes grows downward one generation at a time."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def automaton(width, rows, rule=30, seed=None):
    """`rows` generations of an elementary cellular automaton `width` cells
    wide, as a list of tuples of 0/1. Row 0 is `seed` (default: one live cell
    in the middle); each later cell is bit `left*4 + centre*2 + right` of
    `rule`, with dead cells beyond the edges. Rule 30 by default; 90 gives a
    Sierpinski triangle, 110 a slanting lattice."""
    row = tuple(seed) if seed is not None else tuple(int(i == width // 2) for i in range(width))
    out = [row]
    for _ in range(rows - 1):
        pad = (0,) + row + (0,)
        row = tuple((rule >> (pad[i] * 4 + pad[i + 1] * 2 + pad[i + 2])) & 1 for i in range(width))
        out.append(row)
    return out


def draw_automaton(cv, grid, x, y, cell, p, color=demo.ACCENT, front=demo.INK, gap=0.12):
    """Draw `grid` (from `automaton`) with its top-left at (x, y), cells
    `cell` px square, revealed row by row to progress `p` (0 -> 1). The row
    being born fades in in `front`, settling to `color`. Runs of live cells
    are drawn as single bars. Returns the Box of the whole grid."""
    rows = len(grid)
    shown = vb.clamp01(p) * rows
    inset = cell * gap / 2
    for r in range(min(rows, int(shown) + 1)):
        frac = min(1.0, shown - r)
        if frac <= 0:
            break
        newest = shown - r < 2 and p < 1
        ink = front if newest else color
        row, c = grid[r], 0
        while c < len(row):
            if not row[c]:
                c += 1
                continue
            start = c
            while c < len(row) and row[c]:
                c += 1
            cv.rect(x + start * cell + inset, y + r * cell + inset, (c - start) * cell - 2 * inset,
                    cell - 2 * inset, ink, alpha=frac)
    cols = len(grid[0]) if grid else 0
    return vb.Box(x, y, cols * cell, rows * cell)


COLS, ROWS, CELL = 141, 70, 6
GRID = automaton(COLS, ROWS)


def draw(n, cv):
    x, y = (demo.W - COLS * CELL) / 2, (demo.H - ROWS * CELL) / 2
    box = draw_automaton(cv, GRID, x, y, CELL, demo.phase(n, 0.2, 2.6))
    cv.mark('grid', *box)


CAPABILITY = Capability(
    id='rule-30-automaton',
    name='Rule 30 automaton',
    family='particles',
    group='Cellular automata',
    aliases=('rule 30', 'elementary cellular automaton', 'Wolfram rule 30'),
    definition='Rows of square cells appear one under another from a single seed cell, each cell switched on '
               'or off by a fixed rule on the three above it, spreading into a chaotic triangular pattern.',
    phrasings=('a pixel pattern that grows down the screen row by row from one dot',
               'a cellular automaton building a messy triangle of squares',
               'generative grid art that unfolds one line at a time'),
    related=('pattern-tiling', 'random-stagger', 'wave-function-collapse', 'grid-diagonal-stagger',
             'recursive-tree', 'sierpinski-gasket'),
    api=('videobuilder.capabilities.particles.rule_30_automaton.draw_automaton',
         'videobuilder.capabilities.particles.rule_30_automaton.automaton'),
    demo=lambda: demo.film(draw),
)

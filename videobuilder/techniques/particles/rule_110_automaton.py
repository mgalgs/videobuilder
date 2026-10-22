"""Rule 110 automaton: a row of on/off cells where each new row is worked out
from the one above by rule 110, drawn generation by generation down the frame
so the pattern of triangles and drifting diagonal structures grows as you
watch."""
import math

from .. import _demo as demo
from ..schema import Technique


def rule_step(row, rule=110):
    """The next generation of `row` (a sequence of 0/1) under elementary rule
    `rule`: each cell reads itself and its two neighbours as a 3-bit number and
    takes that bit of `rule`. Cells beyond the edges count as 0."""
    padded = (0, *row, 0)
    return tuple((rule >> (padded[i] << 2 | padded[i + 1] << 1 | padded[i + 2])) & 1
                 for i in range(len(row)))


def generations(width, count, seed=None, rule=110):
    """`count` rows of `width` cells, the first `seed` (default: one live cell
    at the right edge, which rule 110 grows leftwards) and each after it one
    `rule_step` on."""
    row = tuple(seed) if seed is not None else (0,) * (width - 1) + (1,)
    if len(row) != width:
        raise ValueError(f'seed has {len(row)} cells, width is {width}')
    rows = [row]
    for _ in range(count - 1):
        rows.append(rule_step(rows[-1], rule))
    return rows


def draw_automaton(cv, rows, x, y, cell, p, color, head=None, gap=0.0):
    """Draw `rows` (from `generations`) as a grid of `cell`-px squares from
    the top-left (x, y), revealed down the grid as `p` runs 0 -> 1: the first
    row shows at once, the last at 1. The newest row is drawn in `head` (if
    given) with a thin scan line under it. `gap` px is left between cells.
    Returns the number of rows shown."""
    shown = 1 + math.floor(max(0.0, min(1.0, p)) * (len(rows) - 1))
    size = cell - gap
    for r in range(shown):
        ink = head if head and r == shown - 1 and shown < len(rows) else color
        row, c = rows[r], 0
        while c < len(row):  # one rect per run of live cells
            if row[c]:
                start = c
                while c < len(row) and row[c]:
                    c += 1
                cv.rect(x + start * cell, y + r * cell, (c - start) * cell - gap, size, ink)
            else:
                c += 1
    if head and shown < len(rows):
        cv.line(x, y + shown * cell + 1, x + len(rows[0]) * cell, y + shown * cell + 1, head, width=2)
    return shown


COLS, ROWS, CELL = 128, 84, 5


def draw(n, cv):
    w, h = COLS * CELL, ROWS * CELL
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cv.outline(x - 6, y - 6, w + 12, h + 12, demo.LINE, width=2)
    draw_automaton(cv, generations(COLS, ROWS), x, y, CELL, demo.phase(n, 0.2, 2.6), demo.TEAL,
                   head=demo.ACCENT, gap=1)
    cv.mark('grid', x, y, w, h)


TECHNIQUE = Technique(
    id='rule-110-automaton',
    name='Rule 110 automaton',
    family='particles',
    group='Cellular automata',
    aliases=('Turing-complete automaton', 'elementary cellular automaton', 'rule 110'),
    definition='A line of on and off cells rewrites itself row after row by one simple neighbour rule, '
               'stacking into a lattice of triangles and slanted structures that drift across it.',
    phrasings=('a cellular automaton growing down the screen one row at a time',
               'that rule 110 pattern of little triangles building line by line',
               'a generative grid of pixels where each row is computed from the row above'),
    related=('reaction-diffusion', 'maze-carving', 'recursive-tree', 'recursive-rectangle-subdivision',
             'overlapping-action', 'geometric-loop'),
    api=('videobuilder.techniques.particles.rule_110_automaton.draw_automaton',
         'videobuilder.techniques.particles.rule_110_automaton.generations',
         'videobuilder.techniques.particles.rule_110_automaton.rule_step'),
    demo=lambda: demo.film(draw),
)

"""Grid Diagonal Stagger: each cell of a grid waits by its row plus its
column before it animates, so the motion travels across the grid as a
diagonal front from one corner to the opposite one."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def grid_delay(row, col, rows, cols, corner='top-left'):
    """How far along the diagonal cell (`row`, `col`) sits, 0 at `corner`
    ('top-left', 'top-right', 'bottom-left' or 'bottom-right') and 1 at the
    opposite corner. Cells on the same anti-diagonal share a value."""
    if 'bottom' in corner:
        row = rows - 1 - row
    if 'right' in corner:
        col = cols - 1 - col
    span = rows + cols - 2
    return (row + col) / span if span else 0.0


def grid_stagger(p, row, col, rows, cols, spread=0.6, corner='top-left', ease=vb.linear):
    """Cell (`row`, `col`)'s own progress 0 -> 1 at overall progress `p`.
    The first cell starts at `p` = 0 and the last finishes at 1; `spread`
    (0..1) is the share of the whole spent waiting for the diagonal to
    arrive, so each cell animates over the remaining `1 - spread`. `ease`
    shapes each cell's own run."""
    spread = vb.clamp01(spread)
    start = spread * grid_delay(row, col, rows, cols, corner)
    span = 1 - spread
    return ease(vb.clamp01((p - start) / span)) if span > 0 else float(p >= start)


ROWS, COLS, SIZE, GAP = 6, 10, 52, 12


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.4)
    gw, gh = COLS * SIZE + (COLS - 1) * GAP, ROWS * SIZE + (ROWS - 1) * GAP
    x0, y0 = (demo.W - gw) / 2, (demo.H - gh) / 2
    for r in range(ROWS):
        for c in range(COLS):
            x, y = x0 + c * (SIZE + GAP), y0 + r * (SIZE + GAP)
            cv.outline(x, y, SIZE, SIZE, demo.LINE, width=2, radius=10, alpha=0.6)  # the empty slot
            q = grid_stagger(p, r, c, ROWS, COLS, spread=0.7)
            if q <= 0:
                continue
            s = SIZE * max(0.0, vb.ease_out_back(q))
            cx, cy = x + SIZE / 2, y + SIZE / 2
            cv.rect(cx - s / 2, cy - s / 2, s, s, demo.ACCENT, radius=10 * s / SIZE, alpha=min(1.0, q * 3))
    cv.mark('grid', x0, y0, gw, gh)


TECHNIQUE = Technique(
    id='grid-diagonal-stagger',
    name='Grid Diagonal Stagger',
    family='principles',
    group='Stagger',
    aliases=('grid stagger', 'diagonal wave stagger', 'matrix stagger', 'grid index stagger',
             'tile wave grid', 'index-based delay'),
    definition='Tiles in a grid start their animation one after another by row plus column, '
               'so the change rolls across the grid as a diagonal front from one corner to the other.',
    phrasings=('make the grid tiles pop in from the top-left corner in a diagonal wave',
               'stagger the grid so it fills in corner to corner',
               'have the squares appear in a cascade that sweeps diagonally across'),
    related=('linear-repeater-stagger', 'scale-tile-wave', 'bento-grid-reveal', 'grid-wave-loader',
             'pattern-tiling', 'truchet-tiles'),
    api=('videobuilder.techniques.principles.grid_diagonal_stagger.grid_stagger',
         'videobuilder.techniques.principles.grid_diagonal_stagger.grid_delay'),
    demo=lambda: demo.film(draw),
)

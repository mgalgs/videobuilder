"""Isometric Bar Rise: a set of boxes drawn in isometric projection grows up
out of a flat floor grid, one after another, into a 3D-looking bar chart or
little skyline."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba
from ...looks import kit as looks

COS, SIN = math.cos(math.pi / 6), math.sin(math.pi / 6)


def iso(ox, oy, gx, gy, z=0.0, tile=100.0):
    """Grid point (gx, gy) at height `z` pixels -> screen (x, y). The grid
    origin sits at (ox, oy); +gx runs down-right, +gy down-left, `z` up."""
    return ox + (gx - gy) * tile * COS, oy + (gx + gy) * tile * SIN - z


def shade(color, k):
    """`color` darkened by `k` (0 keeps it, 1 is black), as an (r, g, b) tuple."""
    r, g, b, _ = rgba(color)
    return tuple(round(255 * c * (1 - k)) for c in (r, g, b))


def draw_iso_box(cv, ox, oy, gx, gy, height, color, tile=100.0, size=0.8, outline=None):
    """One isometric box standing on grid cell (gx, gy), `size` of the cell
    wide and centred in it, `height` pixels tall: a lit top face in `color`
    and the two visible side faces in darker shades. Returns the screen point
    at the centre of its top face (for a label)."""
    m = (1 - size) / 2
    x0, y0, x1, y1 = gx + m, gy + m, gx + m + size, gy + m + size
    h = max(0.0, height)
    P = lambda a, b, z: iso(ox, oy, a, b, z, tile)  # noqa: E731
    line = dict(outline=outline, width=1.5) if outline else {}
    left = [P(x0, y1, 0), P(x1, y1, 0), P(x1, y1, h), P(x0, y1, h)]
    right = [P(x1, y1, 0), P(x1, y0, 0), P(x1, y0, h), P(x1, y1, h)]
    top = [P(x0, y0, h), P(x1, y0, h), P(x1, y1, h), P(x0, y1, h)]
    if h > 0:
        looks.fill(cv, left, shade(color, 0.28), **line)
        looks.fill(cv, right, shade(color, 0.48), **line)
    looks.fill(cv, top, color, **line)
    return P((x0 + x1) / 2, (y0 + y1) / 2, h)


def draw_iso_floor(cv, ox, oy, cols, rows, tile=100.0, color=demo.LINE, width=2):
    """The flat isometric grid of `cols` x `rows` cells the bars stand on."""
    for i in range(cols + 1):
        looks.outline(cv, [iso(ox, oy, i, 0, 0, tile), iso(ox, oy, i, rows, 0, tile)], color, width)
    for j in range(rows + 1):
        looks.outline(cv, [iso(ox, oy, 0, j, 0, tile), iso(ox, oy, cols, j, 0, tile)], color, width)


def isometric_bar_rise(cv, bars, p, ox, oy, tile=100.0, size=0.8, stagger=0.6, ease=vb.ease_out_back,
                       outline=None, on_top=None):
    """Draw `bars` -- (gx, gy, height, color) tuples -- rising out of the floor
    at progress `p` (0 -> 1). Bars start back to front: each grows over the
    last `1 - stagger` of the run, its start spread across the first
    `stagger`. Painted back to front so nearer bars cover farther ones.
    `on_top(cv, i, (x, y), q)`, if given, runs right after bar `i` is painted
    with its top-centre point and its own progress, so a label sits in the
    same paint order. Returns each bar's (top-centre point, progress), in the
    order given."""
    order = sorted(range(len(bars)), key=lambda i: (bars[i][0] + bars[i][1], bars[i][0]))
    n = max(1, len(bars) - 1)
    out = [None] * len(bars)
    for rank, i in enumerate(order):
        gx, gy, height, color = bars[i]
        start = stagger * rank / n
        q = vb.clamp01((p - start) / (1 - stagger)) if stagger < 1 else float(p >= start)
        top = draw_iso_box(cv, ox, oy, gx, gy, height * ease(q), color, tile, size, outline)
        out[i] = (top, q)
        if on_top:
            on_top(cv, i, top, q)
    return out


COLS, ROWS, TILE = 4, 3, 72
HEIGHTS = ((70, 105, 100, 160),
           (55, 110, 195, 85),
           (40, 80, 65, 120))


def draw(n, cv):
    ox, oy = demo.W / 2 + (ROWS - COLS) * TILE * COS / 2, demo.H / 2 - 40
    draw_iso_floor(cv, ox, oy, COLS, ROWS, TILE)
    bars = [(c, r, HEIGHTS[r][c], demo.ACCENT if (c, r) == (2, 1) else demo.TEAL)
            for r in range(ROWS) for c in range(COLS)]

    def label(cv, i, top, q):
        if q > 0.6:
            demo.word(cv, str(bars[i][2] // 2), top[0], top[1], size=15, color=demo.BG, alpha=(q - 0.6) / 0.4)

    isometric_bar_rise(cv, bars, demo.phase(n, 0.3, 2.4), ox, oy, TILE, outline=demo.BG, on_top=label)
    cv.mark('chart', ox - ROWS * TILE * COS, oy - 200, (COLS + ROWS) * TILE * COS,
            (COLS + ROWS) * TILE * SIN + 200)


CAPABILITY = Capability(
    id='isometric-bar-rise',
    name='Isometric bar rise',
    family='shapes',
    group='Isometric',
    aliases=('isometric column build', 'isometric extrusion rise', '3D-looking tile build'),
    definition='Boxes drawn at an isometric angle push up out of a flat floor grid one after another, '
               'building a chart or block city that looks three-dimensional.',
    phrasings=('make the bars of the chart grow up like 3D blocks seen from an angle',
               'a grid of tiles where columns shoot up into a little isometric skyline',
               'an isometric bar graph whose columns rise into place one by one'),
    related=('bar-grow', 'stacked-bar-build', 'isometric-view', 'isometric-assembly', 'shape-stacking-drop',
             'extrusion'),
    api=('videobuilder.capabilities.shapes.isometric_bar_rise.isometric_bar_rise',
         'videobuilder.capabilities.shapes.isometric_bar_rise.draw_iso_box',
         'videobuilder.capabilities.shapes.isometric_bar_rise.draw_iso_floor',
         'videobuilder.capabilities.shapes.isometric_bar_rise.iso'),
    demo=lambda: demo.film(draw),
)

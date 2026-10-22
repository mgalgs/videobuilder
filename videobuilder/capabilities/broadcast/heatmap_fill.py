"""Heatmap Fill: a grid of empty cells takes on colour cell by cell, each one
shading from a neutral grey to the hue its value earns, in a wave that runs
diagonally from one corner to the other."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

RAMP = ('#1f3b73', '#2f7fb8', '#4fc3b0', '#f2c14e', '#ef5b4c')  # low -> high


def ramp_color(v, ramp=RAMP):
    """The colour for value `v` (0 -> 1) along `ramp`, a sequence of colours
    from low to high, blended linearly between neighbouring stops. Returns an
    (r, g, b) tuple of 0-255 channels."""
    v = vb.clamp01(v) * (len(ramp) - 1)
    i = min(int(v), len(ramp) - 2)
    a, b = vb.rgba(ramp[i]), vb.rgba(ramp[i + 1])
    t = v - i
    return tuple(255 * (x + (y - x) * t) for x, y in zip(a[:3], b[:3]))


def cell_progress(row, col, rows, cols, p, order='diagonal', spread=0.6):
    """How far cell (row, col) of a `rows` x `cols` grid has filled (0 -> 1)
    at overall progress `p`. `order` sets who goes first: 'diagonal' (top
    left to bottom right), 'rows' (row by row, left to right) or 'columns'.
    `spread` is the share of `p` over which the start times are staggered;
    the rest is each cell's own fade."""
    if order == 'rows':
        k = (row * cols + col) / max(1, rows * cols - 1)
    elif order == 'columns':
        k = (col * rows + row) / max(1, rows * cols - 1)
    else:
        k = (row + col) / max(1, rows + cols - 2)
    return vb.clamp01((p - spread * k) / (1 - spread))


def heatmap_fill(cv, values, x, y, w, h, p, ramp=RAMP, neutral=demo.LINE, gap=6, radius=6,
                 order='diagonal', spread=0.6, font=None, label_color=demo.INK):
    """Draw a heatmap of `values` (rows of numbers 0 -> 1) filling the box
    (x, y, w, h), at progress `p` (0 -> 1). Every cell starts `neutral` and
    blends to `ramp_color(value)` in the order `order`, with a small lift
    as it lands. With `font`, each cell shows its value as 0-100 once filled.
    Returns the grid's Box."""
    rows, cols = len(values), len(values[0])
    cw, ch = (w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows
    base = vb.rgba(neutral)
    for r, line in enumerate(values):
        for c, v in enumerate(line):
            q = vb.ease_out_quint(cell_progress(r, c, rows, cols, p, order, spread))
            hot = ramp_color(v, ramp)
            color = tuple(255 * b + (k - 255 * b) * q for b, k in zip(base[:3], hot))
            pop = 1 + 0.12 * math.sin(math.pi * q)
            cx, cy = x + c * (cw + gap) + cw / 2, y + r * (ch + gap) + ch / 2
            sw, sh = cw * pop, ch * pop
            cv.rect(cx - sw / 2, cy - sh / 2, sw, sh, color, radius=radius)
            if font is not None and q > 0.3:
                _centered(cv, str(round(v * 100)), font, cx, cy, label_color, (q - 0.3) / 0.7)
    return vb.Box(x, y, w, h)


def _centered(cv, text, font, cx, cy, color, alpha):
    tw, th = vb.text.block_size([text], font)
    vb.text.draw(cv, [text], font, cx - tw / 2, cy - th / 2, color, alpha=alpha)


def _sample(rows, cols):
    """Smooth demo data: two warm hot spots on a cool field."""
    def v(r, c):
        a = math.exp(-((r - 2) ** 2 + (c - 9) ** 2) / 10)
        b = math.exp(-((r - 6) ** 2 + (c - 3) ** 2) / 8)
        return min(1.0, 0.08 + 0.85 * a + 0.75 * b + 0.06 * math.sin(r * 1.7 + c * 2.3))
    return [[v(r, c) for c in range(cols)] for r in range(rows)]


ROWS, COLS = 8, 12
DATA = _sample(ROWS, COLS)


def draw(n, cv):
    gw, gh = 696, 400
    x, y = (demo.W - gw) / 2 + 14, 52
    small = demo.mono(15, 600)
    for c in range(COLS):
        cw = (gw - 6 * (COLS - 1)) / COLS
        _centered(cv, str(c + 1), small, x + c * (cw + 6) + cw / 2, y - 18, demo.MUTED, 1.0)
    for r in range(ROWS):
        ch = (gh - 6 * (ROWS - 1)) / ROWS
        _centered(cv, 'ABCDEFGH'[r], small, x - 24, y + r * (ch + 6) + ch / 2, demo.MUTED, 1.0)
    box = heatmap_fill(cv, DATA, x, y, gw, gh, demo.phase(n, 0.3, 2.5), font=demo.mono(14, 700))
    cv.mark('heatmap', *box)
    # the legend: the colour scale the cells are filling towards
    lx, ly, lw = demo.W / 2 - 160, y + gh + 30, 320
    steps = 64
    for i in range(steps):
        cv.rect(lx + lw * i / steps, ly, lw / steps + 1, 10, ramp_color(i / (steps - 1)))
    _centered(cv, '0', small, lx - 20, ly + 5, demo.MUTED, 1.0)
    _centered(cv, '100', small, lx + lw + 26, ly + 5, demo.MUTED, 1.0)


CAPABILITY = Capability(
    id='heatmap-fill',
    name='Heatmap fill',
    family='broadcast',
    group='Charts',
    aliases=('grid heatmap reveal', 'matrix color fill', 'heat map reveal'),
    definition='The squares of a data grid start out blank grey and one after another warm into the colour '
               'their number calls for, so the pattern spreads across the matrix in a wave.',
    phrasings=('a grid of squares that colours in by value, sweeping from one corner',
               'animate the heat map so each cell fades from grey to its shade',
               'reveal the matrix chart cell by cell with its colour scale'),
    related=('choropleth-fill', 'thermal-false-color', 'color-fill-rise', 'displacement-map',
             'hexagon-tile-reveal', 'shape-fill-sweep'),
    api=('videobuilder.capabilities.broadcast.heatmap_fill.heatmap_fill',
         'videobuilder.capabilities.broadcast.heatmap_fill.ramp_color',
         'videobuilder.capabilities.broadcast.heatmap_fill.cell_progress'),
    demo=lambda: demo.film(draw),
)

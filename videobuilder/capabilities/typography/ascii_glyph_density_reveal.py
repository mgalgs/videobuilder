"""ASCII Glyph Density Reveal: the same idea as ASCII art render
(`../vfx/ascii_art_render.py`), which keeps the capability -- both pick a
glyph for each cell by brightness and call `draw_density`, this one letting
the grid churn as noise before it settles into a word. This module's own
code stays (a film may still import it), but it is no longer a capability
of its own."""
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'ascii-art-render'

RAMP = ' .:-=+*#%@'  # lightest to densest


def coverage_grid(text, font, cols, rows, cell_w, cell_h, sample=0.5):
    """How much of each cell of a `cols` x `rows` grid (cells `cell_w` x
    `cell_h` px) the word `text` in `font` covers, centred in the grid: a
    list of rows of 0 -> 1. Rendered offscreen at `sample` scale; compute it
    once and reuse it every frame."""
    w, h = cols * cell_w, rows * cell_h
    off = vb.Canvas(w, h, scale=sample)
    tw, th = vb.text.block_size([text], font)
    vb.text.draw(off, [text], font, (w - tw) / 2, (h - th) / 2, '#ffffff')
    data, stride = off.bgra(), off.surface.get_stride()
    pw, ph = off.surface.get_width(), off.surface.get_height()
    grid = []
    for r in range(rows):
        y0, y1 = int(r * cell_h * sample), min(ph, max(int(r * cell_h * sample) + 1, int((r + 1) * cell_h * sample)))
        row = []
        for c in range(cols):
            x0, x1 = int(c * cell_w * sample), min(pw, max(int(c * cell_w * sample) + 1,
                                                        int((c + 1) * cell_w * sample)))
            total = sum(data[y * stride + x * 4 + 3] for y in range(y0, y1) for x in range(x0, x1))
            row.append(total / (255 * max(1, (x1 - x0) * (y1 - y0))))
        grid.append(row)
    return grid


def density_frame(grid, p, seed=0, noise=0.45, changes=36, spread=0.6):
    """The density of every cell at progress `p` (0 -> 1): random noise up to
    `noise` that re-rolls `changes` times across the reveal, each cell easing
    onto its target from `grid` at its own moment (staggered over `spread`
    of the reveal). At `p` 1 it is exactly `grid`."""
    p = vb.clamp01(p)
    step = int(p * changes)
    out = []
    for r, row in enumerate(grid):
        line = []
        for c, target in enumerate(row):
            delay = random.Random(f'{seed}:{r}:{c}').random() * spread
            k = vb.ease_in_out_quart(vb.clamp01((p - delay) / (1 - spread)))
            n = random.Random(f'{seed}:{r}:{c}:{step}').random() * noise
            line.append(n + (target - n) * k)
        out.append(line)
    return out


def draw_density(cv, densities, font, x, y, cell_w, cell_h, color, dim=None, ramp=RAMP):
    """Draw a grid of densities (0 -> 1) from its top-left (x, y) as glyphs
    from `ramp`, densest last. Sparse glyphs fade towards `dim` (default
    `color` at low strength). One text run per row and glyph, so a full
    frame stays cheap. Returns the grid's Box."""
    rows, cols = len(densities), len(densities[0]) if densities else 0
    last = len(ramp) - 1
    for r, row in enumerate(densities):
        levels = [min(last, int(d * last + 0.5)) for d in row]
        for lv in set(levels) - {0}:
            line = ''.join(ramp[lv] if v == lv else ' ' for v in levels)
            t = lv / last
            lo, hi = vb.rgba(dim or color), vb.rgba(color)
            ink = tuple(255 * (a + (b - a) * t) for a, b in zip(lo[:3], hi[:3]))
            vb.text.draw(cv, [line], font, x, y + r * cell_h, ink, alpha=1.0 if dim else 0.3 + 0.7 * t)
    return vb.Box(x, y, cols * cell_w, rows * cell_h)


FONT = demo.mono(12, 700)
CELL_H = 14


@lru_cache(maxsize=None)
def _layout():
    """`(cell_w, cols, rows, coverage grid)`: measured on the first frame,
    not at import, so listing capabilities lays out no text."""
    cell_w = vb.text.measure('@', FONT)
    cols, rows = int(840 // cell_w), int(230 // CELL_H)
    return cell_w, cols, rows, coverage_grid('MOTION', demo.font(190, 900), cols, rows, cell_w, CELL_H)


def __getattr__(name):
    # CELL_W, COLS and ROWS were module constants, and a film may still import them.
    if name in ('CELL_W', 'COLS', 'ROWS'):
        return _layout()[('CELL_W', 'COLS', 'ROWS').index(name)]
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def draw(n, cv):
    cell_w, cols, rows, grid = _layout()
    x, y = (demo.W - cols * cell_w) / 2, (demo.H - rows * CELL_H) / 2
    dens = density_frame(grid, demo.phase(n, 0.3, 2.4), seed=5)
    box = draw_density(cv, dens, FONT, x, y, cell_w, CELL_H, demo.INK, dim=demo.LINE)
    cv.mark('text', *box)

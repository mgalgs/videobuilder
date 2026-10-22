"""ASCII Glyph Density Reveal: a grid of monospaced characters, each picked
by how much ink it should carry, churns as noise and then settles so the
dense glyphs spell out a word."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

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
CELL_W, CELL_H = vb.text.measure('@', FONT), 14
COLS, ROWS = int(840 // CELL_W), int(230 // CELL_H)
_grid = []


def draw(n, cv):
    if not _grid:
        _grid.append(coverage_grid('MOTION', demo.font(190, 900), COLS, ROWS, CELL_W, CELL_H))
    x, y = (demo.W - COLS * CELL_W) / 2, (demo.H - ROWS * CELL_H) / 2
    dens = density_frame(_grid[0], demo.phase(n, 0.3, 2.4), seed=5)
    box = draw_density(cv, dens, FONT, x, y, CELL_W, CELL_H, demo.INK, dim=demo.LINE)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='ascii-glyph-density-reveal',
    name='ASCII glyph density reveal',
    family='typography',
    group='Glyph swaps',
    aliases=('ASCII art type', 'character density text', 'ASCII text reveal'),
    definition='A block of flickering monospaced characters settles so that heavy glyphs gather where '
               'the letters are and light ones fade away, until the word stands out in pure type.',
    phrasings=('make the title appear out of a field of ASCII characters',
               'a wall of random code characters that resolves into the word',
               'build the headline out of dense text symbols like ASCII art'),
    related=('ascii-art-render', 'pixelation-reveal', 'random-order-character-reveal', 'typewriter-reveal',
             'ink-spread-reveal', 'pixel-sort-text'),
    api=('videobuilder.techniques.typography.ascii_glyph_density_reveal.draw_density',
         'videobuilder.techniques.typography.ascii_glyph_density_reveal.density_frame',
         'videobuilder.techniques.typography.ascii_glyph_density_reveal.coverage_grid'),
    demo=lambda: demo.film(draw),
)

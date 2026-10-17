"""Blueprint filter: only the picture's edges, drawn as chalk lines on a
blue sheet ruled with a grid. The lines draw in from the top behind a
bright scan line when the filter comes on (on `age`); after that the scan
line keeps sweeping down, the grid shimmers as a light band travels across
it, and the chalk boils on twos."""
import math

from PIL import Image, ImageChops

from . import Filter, boil, edges, grow, luma, noise, shrink, wave_band, work_factor
from ...ease import clamp01, ease_in_out_quart

PAPER = (26, 74, 140)
GRIDLINE = (74, 128, 196)
CHALK = (234, 244, 255)
DRAW_IN = 0.9      # seconds for the lines to draw in
SWEEP = 2.6        # seconds for the scan line to cross the frame after that


_GRID = {}


def _grid(w, h, u):
    """The ruled grid as an L mask: a thin line every 40 px at 1080, a heavy one every fifth."""
    key = (w, h, round(u, 3))
    if key not in _GRID:
        from PIL import ImageDraw
        m = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(m)
        pitch = max(4.0, 40 * u)
        for axis, length in ((0, w), (1, h)):
            k, p = 0, 0.0
            while p < length:
                width = max(1, round((3 if k % 5 == 0 else 1.5) * u))
                box = (p, 0, p + width - 1, h) if axis == 0 else (0, p, w, p + width - 1)
                d.rectangle(box, fill=255 if k % 5 == 0 else 170)
                p += pitch
                k += 1
        _GRID.clear()
        _GRID[key] = m
    return _GRID[key]


def treat(im, t, age, u):
    w, h = im.size
    k = work_factor(u)
    period = max(8, int(520 * u))
    shimmer = wave_band(w, h, period, 90, 255).crop((0, 0, w + period, h))
    off = int(t * 260 * u) % period
    grid = ImageChops.multiply(_grid(w, h, u), shimmer.crop((off, 0, off + w, h)))
    out = Image.new('RGB', (w, h), PAPER)
    out.paste(GRIDLINE, (0, 0, w, h), grid)
    lines = grow(edges(luma(shrink(im, k)), level=26, blur=0.8, thick=3 * u / k), (w, h))
    chalk = noise(w, h, 300 + boil(t) % 5, blur=0.6).point(lambda v: 255 if v > 70 else 120)
    lines = ImageChops.multiply(lines, chalk)               # broken chalk, boiling on twos
    p = ease_in_out_quart(clamp01(age / DRAW_IN))
    if p < 1:                                               # drawing in from the top
        reveal = int(h * p)
        lines.paste(0, (0, reveal, w, h))
        scan = reveal
    else:
        scan = int(h * ((age - DRAW_IN) / SWEEP % 1.0))
    out.paste(CHALK, (0, 0, w, h), lines)
    glow = max(2, int(60 * u))                              # the scan line and its glow
    for i in range(glow):
        a = int(110 * (1 - i / glow) ** 2)
        y = scan - i
        if 0 <= y < h and a:
            out.paste(CHALK, (0, y, w, y + 1), Image.new('L', (w, 1), a))
    if 0 <= scan < h:
        out.paste(CHALK, (0, scan, w, min(h, scan + max(1, round(3 * u)))))
    return out


FILTER = Filter('blueprint', 'Blueprint filter', 'chalk edges on a shimmering grid, a scan line sweeps', treat, aliases=('line drawing',))

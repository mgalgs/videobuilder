"""Scale tile wave: a grid of tiles each grows and shrinks in place, the
pulse handed from tile to tile so a wave of scale rolls across the grid."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tile_wave(t, dist, period=1.2, wavelength=4.0, lo=0.25, hi=1.0):
    """Scale of one tile at time `t` seconds, `dist` tiles from the wave's
    origin: a cosine pulse between `lo` and `hi` repeating every `period`
    seconds, delayed by `period` for every `wavelength` tiles of distance."""
    s = 0.5 - 0.5 * math.cos(2 * math.pi * (t / period - dist / wavelength))
    return lo + (hi - lo) * s


def draw_tile_wave(cv, box, cols, rows, t, origin=(0.5, 0.5), gap=0.18, color=demo.ACCENT, hot=None,
                   radius=0.22, **kw):
    """Draw a `cols` x `rows` grid of square tiles filling `box` (centred,
    `gap` of a cell between tiles), each scaled about its own centre by
    `tile_wave`. `origin` is where the wave starts, in grid fractions:
    (0.5, 0.5) ripples out from the centre, (0, 0) sweeps diagonally from the
    top left. With `hot`, a tile's colour moves from `color` towards `hot` as
    it grows. `kw` goes to `tile_wave`. Returns the Box the grid covers."""
    cell = min(box.w / cols, box.h / rows)
    x0, y0 = box.x + (box.w - cell * cols) / 2, box.y + (box.h - cell * rows) / 2
    ox, oy = origin[0] * (cols - 1), origin[1] * (rows - 1)
    lo, hi = kw.get('lo', 0.25), kw.get('hi', 1.0)
    side = cell * (1 - gap)
    for r in range(rows):
        for c in range(cols):
            s = tile_wave(t, math.hypot(c - ox, r - oy), **kw)
            w = side * s
            cx, cy = x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell
            cv.rect(cx - w / 2, cy - w / 2, w, w, color, radius=w * radius)
            if hot is not None:
                cv.rect(cx - w / 2, cy - w / 2, w, w, hot, radius=w * radius,
                        alpha=vb.clamp01((s - lo) / ((hi - lo) or 1)) ** 2)
    return vb.Box(x0, y0, cell * cols, cell * rows)


def draw(n, cv):
    box = vb.Box(120, 90, demo.W - 240, demo.H - 180)
    grid = draw_tile_wave(cv, box, 16, 9, n / demo.FPS, color=demo.LINE, hot=demo.ACCENT,
                          period=1.5, wavelength=5.0, lo=0.2)
    cv.mark('grid', *grid)


TECHNIQUE = Technique(
    id='scale-tile-wave',
    name='Scale tile wave',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('tile wave', 'scaling grid wave', 'grid ripple', 'pulse grid'),
    definition='A grid of tiles that each swell and shrink in place, timed so the growth ripples outward '
               'across the grid like a wave.',
    phrasings=('a grid of squares pulsing in a ripple from the middle',
               'tiles that grow and shrink one after another like a wave passing through',
               'a wall of blocks breathing in a rolling pattern'),
    related=('grid-wave-loader', 'wave-function-collapse', 'grid-diagonal-stagger', 'mosaic-tiling',
             'scale-pulse', 'truchet-tiles'),
    api=('videobuilder.techniques.shapes.scale_tile_wave.draw_tile_wave',
         'videobuilder.techniques.shapes.scale_tile_wave.tile_wave'),
    demo=lambda: demo.film(draw),
)

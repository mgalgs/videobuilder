"""Truchet tiles: a grid of square tiles, each holding the same two quarter-circle
arcs in one of two orientations, so the arcs join across tile edges into long
winding lines; turning tiles a quarter turn re-routes the whole maze."""
import math
import random

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def truchet_layout(cols, rows, seed=0):
    """A `rows` x `cols` grid of starting orientations, 0 or 1, from `seed`."""
    rnd = random.Random(seed)
    return [[rnd.randrange(2) for _ in range(cols)] for _ in range(rows)]


def draw_truchet_tile(cv, cx, cy, size, turn=0.0, color=demo.ACCENT, width=None, grow=1.0, alpha=1.0):
    """One tile centred at (cx, cy): two quarter arcs of radius `size / 2`
    centred on opposite corners, so each arc joins the midpoints of two
    adjacent edges. `turn` rotates it in quarter turns (fractions animate);
    `grow` (0 -> 1) draws the arcs on from their ends."""
    c = cv.ctx
    r = size / 2
    sweep = math.pi / 2 * vb.clamp01(grow)
    if sweep <= 0:
        return
    c.save()
    c.translate(cx, cy)
    c.rotate(turn * math.pi / 2)
    c.set_line_width(width if width is not None else size * 0.16)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    cr, cg, cb, ca = rgba(color)
    c.set_source_rgba(cr, cg, cb, ca * alpha)
    for ax, ay, a0 in ((-r, -r, 0.0), (r, r, math.pi)):
        mid = a0 + math.pi / 4
        c.new_path()
        c.arc(ax, ay, r, mid - sweep / 2, mid + sweep / 2)
        c.stroke()
    c.restore()


def truchet_tiles(cv, size=60, seed=0, box=None, turns=None, color=demo.ACCENT, width=None, grow=1.0):
    """Fill `box` (default the whole canvas) with Truchet tiles of edge `size`,
    oriented from `seed`. `turns(i, j)` -> extra quarter turns for the tile at
    column `i`, row `j` (fractions animate the turn); `color` is a colour or a
    callable `(i, j, turn) -> colour`; `grow` draws every arc on. The grid is
    centred, overhanging the box edges so no part-tile gap shows."""
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    cols, rows = math.ceil(w / size), math.ceil(h / size)
    ox, oy = x + (w - cols * size) / 2, y + (h - rows * size) / 2
    layout = truchet_layout(cols, rows, seed)
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    for j, row in enumerate(layout):
        for i, o in enumerate(row):
            extra = turns(i, j) if turns else 0.0
            col = color(i, j, extra) if callable(color) else color
            draw_truchet_tile(cv, ox + (i + 0.5) * size, oy + (j + 0.5) * size, size, o + extra, col, width, grow)
    c.restore()


SIZE = 60
_FLIP = random.Random(7)
FLIPS = {(i, j) for j in range(9) for i in range(16) if _FLIP.random() < 0.45}   # tiles the wave turns


def _turn_at(n):
    """Per-tile quarter turns at frame `n`: a diagonal wave sweeps left to right
    and turns the chosen tiles once each, overshooting a little as they land."""
    t = n / demo.FPS

    def turns(i, j):
        if (i, j) not in FLIPS:
            return 0.0
        start = 0.95 + (i + j * 0.6) * 0.06
        return vb.ease_out_back(vb.clamp01((t - start) / 0.45))
    return turns


def _color(i, j, turn):
    """Accent at rest; teal while a tile is mid-turn, so the moving ones read."""
    k = math.sin(math.pi * min(1.0, max(0.0, turn)))
    a, b = rgba(demo.ACCENT), rgba(demo.TEAL)
    return tuple(round(255 * (a[m] + (b[m] - a[m]) * k)) for m in range(3))


def draw(n, cv):
    grow = vb.ease_in_out_quart(demo.phase(n, 0.1, 0.8))
    truchet_tiles(cv, SIZE, seed=3, turns=_turn_at(n), color=_color, grow=grow)
    cv.mark('tiles', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='truchet-tiles',
    name='Truchet tiles',
    family='particles',
    group='Tiling & patterns',
    aliases=('Truchet pattern', 'quarter-circle tiles', 'Smith tiles', 'random arc tiling'),
    definition='A grid of square tiles, each carrying the same pair of corner arcs turned one of two ways, '
               'whose arcs link up into flowing maze-like lines that re-route as tiles rotate.',
    phrasings=('a background of curvy lines made from little rotated tiles',
               'a maze of swirling arcs where squares flip around and change the paths',
               'random quarter-circle tile pattern that shifts over time'),
    related=('mosaic-tiling', 'pattern-tiling', 'tessellation-triangle-flip', 'tile-flip', 'domino-toppling',
             'scale-tile-wave'),
    api=('videobuilder.capabilities.particles.truchet_tiles.truchet_tiles',
         'videobuilder.capabilities.particles.truchet_tiles.draw_truchet_tile',
         'videobuilder.capabilities.particles.truchet_tiles.truchet_layout'),
    demo=lambda: demo.film(draw),
)

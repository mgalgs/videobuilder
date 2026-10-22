"""Hexagon Tile Reveal: a honeycomb of hexagons pops in tile by tile,
spreading out ring by ring from a starting cell until the frame is covered."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def hex_grid(x, y, w, h, size, origin=None):
    """Pointy-top hexagon centres of circumradius `size` covering the box
    (x, y, w, h), one cell centred on `origin` (default the box centre).
    Returns `(cx, cy, ring)` triples sorted by `ring`, the cell's hex-step
    distance from the origin cell."""
    ox, oy = origin or (x + w / 2, y + h / 2)
    dx, dy = math.sqrt(3) * size, 1.5 * size
    rows = math.ceil(max(oy - y, y + h - oy) / dy) + 1
    cols = math.ceil(max(ox - x, x + w - ox) / dx) + 2
    out = []
    for r in range(-rows, rows + 1):
        for q in range(-cols - rows, cols + rows + 1):   # axial coordinates
            cx, cy = ox + dx * (q + r / 2), oy + dy * r
            if x - size <= cx <= x + w + size and y - size <= cy <= y + h + size:
                out.append((cx, cy, (abs(q) + abs(r) + abs(q + r)) // 2))
    out.sort(key=lambda t: t[2])
    return out


def hexagon(cv, cx, cy, size, color, alpha=1.0, angle=0.0):
    """A filled pointy-top hexagon of circumradius `size` centred at (cx, cy),
    turned by `angle` radians."""
    c = cv.ctx
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3 + angle
        (c.move_to if i == 0 else c.line_to)(cx + size * math.cos(a), cy + size * math.sin(a))
    c.close_path()
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()


def hex_reveal(cv, p, x, y, w, h, size=60, colors=('#f2b705',), origin=None, gap=4, pop=0.25, jitter=0.35,
               seed=0):
    """Draw a honeycomb over (x, y, w, h) revealed to progress `p` (0 -> 1).
    Tiles start ring by ring outward from `origin`, each with a small random
    head start of up to `jitter` of a ring so the edge looks organic, and each
    grows from nothing to full size with an overshoot over `pop` of the
    reveal. A tile's colour is `colors[ring % len(colors)]`; `gap` is the
    grout between tiles. The last tile is in place at `p` = 1."""
    tiles = hex_grid(x, y, w, h, size, origin)
    rings = tiles[-1][2] + 1 if tiles else 1
    rng = random.Random(seed)
    for cx, cy, ring in tiles:
        start = (ring + jitter * (1 - rng.random())) / (rings + jitter) * (1 - pop)
        k = vb.clamp01((p - start) / pop)
        if k <= 0:
            continue
        s = (size - gap / 2) * vb.ease_out_back(k)
        hexagon(cv, cx, cy, s, colors[ring % len(colors)], angle=(1 - k) * math.pi / 3)


def draw(n, cv):
    hex_reveal(cv, demo.phase(n, 0.3, 2.5), 0, 0, demo.W, demo.H, size=64,
               colors=('#f2b705', '#7b86f5', '#5a63c4'), seed=3)
    cv.mark('honeycomb', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='hexagon-tile-reveal',
    name='Hexagon tile reveal',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('honeycomb reveal', 'hex grid fill', 'hex mosaic build'),
    definition='Hexagons pop into place one after another, spreading out from a single cell '
               'until a honeycomb fills the screen.',
    phrasings=('fill the screen with a honeycomb that grows outward',
               'hexagon tiles popping on in rings from the middle',
               'build the background out of hex cells one by one'),
    related=('hexbin-density-build', 'tile-grid-title-reveal', 'tile-flip', 'bento-grid-reveal',
             'mosaic-tiling', 'pattern-tiling'),
    api=('videobuilder.capabilities.shapes.hexagon_tile_reveal.hex_reveal',
         'videobuilder.capabilities.shapes.hexagon_tile_reveal.hex_grid',
         'videobuilder.capabilities.shapes.hexagon_tile_reveal.hexagon'),
    demo=lambda: demo.film(draw),
)

"""Tessellation Triangle Flip: a plane tiled with triangles, each turning over
on its own axis like a card, so a wave of flips sweeps across the pattern and
leaves the other face showing."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def triangle_grid(x, y, w, h, side):
    """Equilateral triangles of edge `side` tiling the box (x, y, w, h), rows
    alternating up- and down-pointing, overhanging the edges so no gap shows.
    Returns `(points, (cx, cy))` per triangle: three (x, y) corners, apex
    first, and the triangle's centre."""
    th = side * math.sqrt(3) / 2
    tris = []
    for r in range(-1, int(h / th) + 2):
        top, bot = y + r * th, y + (r + 1) * th
        shift = side / 2 if r % 2 else 0.0
        for c in range(-2, int(w / (side / 2)) + 3):
            left = x + shift + c * side / 2
            if c % 2 == 0:   # pointing up: apex at the top
                pts = ((left + side / 2, top), (left, bot), (left + side, bot))
            else:            # pointing down: apex at the bottom
                pts = ((left + side / 2, bot), (left, top), (left + side, top))
            tris.append((pts, (left + side / 2, (top + bot) / 2)))
    return tris


def draw_flip(cv, points, p, front, back, shade=0.45):
    """One triangle at flip progress `p` (0 -> 1), turning about the vertical
    line through its apex: the corners close in on that line, then open out
    again showing the `back` colour. Near edge-on it darkens by up to `shade`."""
    turn = math.cos(math.pi * vb.clamp01(p))
    ax = points[0][0]
    pts = [(ax + (px - ax) * abs(turn), py) for px, py in points]
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    r, g, b, a = rgba(front if turn >= 0 else back)
    dim = 1 - shade * (1 - abs(turn))
    c.set_source_rgba(r * dim, g * dim, b * dim, a)
    c.fill()


def tessellation_flip(cv, p, front, back, box=None, side=120, spread=0.6, angle=-0.5, gap=0.0):
    """Tile `box` (default the whole canvas) with triangles and flip them all
    in a diagonal wave at progress `p` (0 -> 1). `front` and `back` are colours,
    or callables `(cx, cy) -> colour` for a pattern. `spread` is the share of
    `p` the wave takes to cross (each triangle flips over the rest); `angle`
    (radians) sets the wave's direction. `gap` px shrinks each triangle toward
    its centre so the grid lines show through."""
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    tris = triangle_grid(x, y, w, h, side)
    dx, dy = math.cos(angle), math.sin(angle)
    along = [(cx - x) * dx + (cy - y) * dy for _, (cx, cy) in tris]
    lo, hi = min(along), max(along)
    for (pts, (cx, cy)), d in zip(tris, along):
        start = spread * (d - lo) / (hi - lo)
        q = vb.ease_in_out_quart(vb.clamp01((p - start) / (1 - spread)))
        if gap:
            k = 1 - gap / side * 2
            pts = tuple((cx + (px - cx) * k, cy + (py - cy) * k) for px, py in pts)
        f = front(cx, cy) if callable(front) else front
        b = back(cx, cy) if callable(back) else back
        draw_flip(cv, pts, q, f, b)


def _back(cx, cy):
    """The revealed face: teal shading into the accent across the frame."""
    t = vb.clamp01(cx / demo.W * 0.8 + cy / demo.H * 0.2)
    a, b = rgba(demo.TEAL), rgba(demo.ACCENT)
    return tuple(round(255 * (a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _front(cx, cy):
    """The starting face: two close greys in a checker, so each tile reads."""
    k = round(cx / 60) + round(cy / 100)
    return demo.LINE if k % 2 else '#202228'


def draw(n, cv):
    tessellation_flip(cv, demo.phase(n, 0.0, 3.4), _front, _back, side=150, spread=0.75, gap=3)


CAPABILITY = Capability(
    id='tessellation-triangle-flip',
    name='Tessellation triangle flip',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('triangle flip', 'triangle tile flip', 'flipping triangle grid', 'triangle mosaic flip'),
    definition='A surface tiled with triangles turns over piece by piece in a sweeping wave, '
               'each triangle spinning on its axis to show a new colour on its back.',
    phrasings=('a grid of triangles that flip over one after another across the screen',
               'make the background a triangle pattern and have the tiles turn over in a wave',
               'triangles rotating like cards to change the pattern'),
    related=('tile-flip', 'mosaic-tiling', 'penrose-tiling', 'tesseract-rotation', 'flip', 'truchet-tiles'),
    api=('videobuilder.capabilities.shapes.tessellation_triangle_flip.tessellation_flip',
         'videobuilder.capabilities.shapes.tessellation_triangle_flip.draw_flip',
         'videobuilder.capabilities.shapes.tessellation_triangle_flip.triangle_grid'),
    demo=lambda: demo.film(draw),
)

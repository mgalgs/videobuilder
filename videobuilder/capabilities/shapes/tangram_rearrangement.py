"""Tangram Rearrangement: a set of flat pieces that fit together as one shape
lift apart, each turning and gliding on its own, and settle again as a
different silhouette."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _centroid(pts):
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


def _heading(pts):
    (x0, y0), (x1, y1) = pts[0], pts[1]
    return math.atan2(y1 - y0, x1 - x0)


def rearrange(home, target, p, stagger=0.35, ease=vb.ease_in_out_quart, lift=0.0):
    """Each piece at progress `p` (0 -> 1) of the move from layout `home` to
    layout `target`, as `(points, t)` pairs in piece order, `t` that piece's
    own eased progress.

    `home` and `target` are lists of polygons (point lists), the same piece
    at the same index with its corners in the same order, each target a
    turned-and-moved copy of its home (no flips). A piece glides its centre
    in a straight line and turns the short way round. `stagger` (0 -> 1) is
    how much of the move the start times spread over, so pieces leave one
    after another in list order; `lift` bows each path sideways by that
    fraction of its length, for a looser, tossed feel."""
    n = len(home)
    span = 1 - stagger
    out = []
    for i, (a, b) in enumerate(zip(home, target)):
        start = stagger * i / max(1, n - 1)
        t = ease(vb.clamp01((p - start) / span)) if span > 0 else float(p >= start)
        (ax, ay), (bx, by) = _centroid(a), _centroid(b)
        turn = (_heading(b) - _heading(a) + math.pi) % (2 * math.pi) - math.pi
        bow = lift * math.sin(math.pi * t) * (1 if i % 2 else -1)
        cx = ax + (bx - ax) * t - (by - ay) * bow
        cy = ay + (by - ay) * t + (bx - ax) * bow
        c, s = math.cos(turn * t), math.sin(turn * t)
        pts = [(cx + (x - ax) * c - (y - ay) * s, cy + (x - ax) * s + (y - ay) * c) for x, y in a]
        out.append((pts, t))
    return out


def draw_rearrange(cv, home, target, p, colors, seam=demo.BG, seam_width=2, shadow=True, **kw):
    """Draw the pieces of `rearrange(home, target, p, **kw)` filled with
    `colors` (one per piece, cycled), thin `seam` edges between them so the
    cuts read. A piece in flight sits on top of resting ones with a soft
    shadow under it."""
    pieces = rearrange(home, target, p, **kw)
    order = sorted(range(len(pieces)), key=lambda i: 0 < pieces[i][1] < 1)
    ctx = cv.ctx
    for i in order:
        pts, t = pieces[i]
        air = math.sin(math.pi * t)
        if shadow and air > 0.01:
            cv.shape_shadow(pts, dy=14 * air, blur=18, color=(0, 0, 0, 0.45 * air))
        ctx.new_path()
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(colors[i % len(colors)]))
        ctx.fill_preserve()
        ctx.set_source_rgba(*vb.rgba(seam))
        ctx.set_line_width(seam_width)
        ctx.set_line_join(1)  # round
        ctx.stroke()
    return [pts for pts, _ in pieces]


# The seven classic pieces cut from a 4 x 4 square, in square units: two large
# triangles, a medium one, two small ones, a square and a parallelogram.
SQUARE = [
    [(0, 0), (4, 0), (2, 2)],
    [(0, 0), (2, 2), (0, 4)],
    [(4, 2), (4, 4), (2, 4)],
    [(4, 0), (4, 2), (3, 1)],
    [(1, 3), (2, 2), (3, 3)],
    [(2, 2), (3, 1), (4, 2), (3, 3)],
    [(0, 4), (1, 3), (3, 3), (2, 4)],
]

# The same pieces as a house: roof, a 4 x 2 body, a chimney on the roof's
# slope and a sun up to the left. Corner order matches SQUARE piece for piece.
HOUSE = [
    [(4, 0), (0, 0), (2, -2)],
    [(4, 0), (2, 2), (0, 0)],
    [(2, 2), (0, 2), (0, 0)],
    [(4, 0), (4, 2), (3, 1)],
    [(2, 2), (3, 1), (4, 2)],
    [(-2.5, -3.5), (-1.5, -4.5), (-0.5, -3.5), (-1.5, -2.5)],
    [(3, -3), (4, -2), (4, 0), (3, -1)],
]


def fit(layout, cx, cy, unit):
    """`layout` (polygons in square units) scaled by `unit` and centred on (cx, cy)."""
    xs = [x for poly in layout for x, _ in poly]
    ys = [y for poly in layout for _, y in poly]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [[(cx + (x - mx) * unit, cy + (y - my) * unit) for x, y in poly] for poly in layout]


COLORS = (demo.ACCENT, demo.TEAL, '#f2b33d', '#7c83f2', '#e9e6df', '#b4b9ff', '#c8902a')


def draw(n, cv):
    unit = 66
    home = fit(SQUARE, demo.W / 2, demo.H / 2, unit)
    house = fit(HOUSE, demo.W / 2, demo.H / 2, unit)
    pts = draw_rearrange(cv, home, house, demo.phase(n, 0.5, 2.5), COLORS, stagger=0.4, lift=0.18)
    xs = [x for poly in pts for x, _ in poly]
    ys = [y for poly in pts for _, y in poly]
    cv.mark('pieces', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='tangram-rearrangement',
    name='Tangram rearrangement',
    family='shapes',
    group='Shape morphing',
    aliases=('tangram puzzle transform', 'piece reflow', 'tangram morph'),
    definition='A shape made of a few flat geometric pieces comes apart, and each piece spins and slides '
               'into a new spot until together they make a completely different picture.',
    phrasings=('the square breaks into puzzle pieces that rebuild themselves as a house',
               'triangles shuffle around and click together into a new shape',
               'like a tangram puzzle solving itself on screen'),
    related=('twist-deformer', 'tessellation-triangle-flip', 'polygon-subdivision', 'bauhaus-geometric-shuffle',
             'recursive-rectangle-subdivision', 'grid-reflow-shuffle'),
    api=('videobuilder.techniques.shapes.tangram_rearrangement.draw_rearrange',
         'videobuilder.techniques.shapes.tangram_rearrangement.rearrange',
         'videobuilder.techniques.shapes.tangram_rearrangement.fit',
         'videobuilder.techniques.shapes.tangram_rearrangement.SQUARE',
         'videobuilder.techniques.shapes.tangram_rearrangement.HOUSE'),
    demo=lambda: demo.film(draw),
)

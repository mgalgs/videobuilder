"""Sierpinski Gasket: the chaos game. A point hops halfway toward a corner of
a triangle picked at random, leaving a dot each time; thousands of hops build
up a triangle full of ever-smaller triangular holes."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def chaos_game(corners, count, seed=0, start=None, ratio=0.5, skip=8):
    """`count` points of the chaos game as `(x, y, corner)` tuples: from
    `start` (default: the corners' centroid) each step moves `ratio` of the way
    toward a corner of `corners` chosen at random, `corner` being its index.
    The first `skip` hops, still settling onto the fractal, are dropped. Three
    corners and 0.5 give the Sierpinski gasket; the same `seed` gives the same
    points."""
    rng = random.Random(seed)
    x, y = start or (sum(c[0] for c in corners) / len(corners), sum(c[1] for c in corners) / len(corners))
    out = []
    for i in range(count + skip):
        k = rng.randrange(len(corners))
        x += (corners[k][0] - x) * ratio
        y += (corners[k][1] - y) * ratio
        if i >= skip:
            out.append((x, y, k))
    return out


def triangle(cx, cy, side):
    """The corners of an upright equilateral triangle of `side` centred on its
    bounding box at (cx, cy): top, bottom right, bottom left."""
    h = side * math.sqrt(3) / 2
    return ((cx, cy - h / 2), (cx + side / 2, cy + h / 2), (cx - side / 2, cy + h / 2))


def draw_points(cv, points, colors, size=2.0, alpha=1.0):
    """Draw chaos-game `points` as small squares, coloured by the corner each
    hopped toward (`colors[corner]`); one fill per colour, so tens of thousands
    of points stay cheap."""
    c = cv.ctx
    for k, color in enumerate(colors):
        c.new_path()
        for x, y, corner in points:
            if corner == k:
                c.rectangle(x - size / 2, y - size / 2, size, size)
        c.set_source_rgba(*vb.rgba(color, alpha))
        c.fill()


SIDE = 520
CORNERS = triangle(demo.W / 2, demo.H / 2, SIDE)
COLORS = (demo.ACCENT, demo.TEAL, demo.INK)
TOTAL = 30000


@lru_cache(maxsize=1)
def _points():
    return chaos_game(CORNERS, TOTAL, seed=3, skip=0)


def draw(n, cv):
    pts = _points()
    p = demo.phase(n, 0.2, 2.6)
    shown = max(1, round(TOTAL * p ** 3))   # a few slow, visible hops, then a flood
    draw_points(cv, pts[:shown], COLORS, size=1.4, alpha=0.9)
    if shown < 60:   # early on, show each hop: a line to the chosen corner and the point travelling it
        x, y, k = pts[shown - 1]
        px, py = pts[shown - 2][:2] if shown > 1 else (demo.W / 2, sum(c[1] for c in CORNERS) / 3)
        cv.line(px, py, *CORNERS[k], demo.MUTED, width=1.5, alpha=0.7)
        demo.dot(cv, x, y, 6, color=COLORS[k])
    for (x, y), color in zip(CORNERS, COLORS):
        demo.dot(cv, x, y, 8, color=color)
    xs, ys = [c[0] for c in CORNERS], [c[1] for c in CORNERS]
    cv.mark('gasket', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='sierpinski-gasket',
    name='Sierpinski gasket',
    family='particles',
    group='Fractals',
    aliases=('Sierpinski triangle', 'chaos game'),
    definition='A dot repeatedly leaps half the distance to a randomly picked corner of a triangle, and the '
               'trail of landings grows into a triangle riddled with nested triangular holes.',
    phrasings=('dots pile up into that triangle made of smaller and smaller triangles',
               'a fractal triangle that fills in from random points',
               'show the chaos game drawing a Sierpinski triangle'),
    related=('hopalong-attractor', 'circle-pop', 'circle-packing', 'de-jong-attractor', 'wiggle-path',
             'delaunay-triangle-mesh'),
    api=('videobuilder.techniques.particles.sierpinski_gasket.chaos_game',
         'videobuilder.techniques.particles.sierpinski_gasket.draw_points',
         'videobuilder.techniques.particles.sierpinski_gasket.triangle'),
    demo=lambda: demo.film(draw),
)

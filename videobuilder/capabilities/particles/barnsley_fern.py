"""Barnsley Fern: a single point hops around under four randomly chosen affine
maps, and every place it lands is plotted; the dust settles into a fern."""
import random
from functools import lru_cache

from PIL import Image as PILImage, ImageDraw

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# (a, b, c, d, e, f, weight): x' = a x + b y + e, y' = c x + d y + f. In order:
# the stem, the ever-smaller copy of the whole frond, the left and right leaflets.
MAPS = ((0.0, 0.0, 0.0, 0.16, 0.0, 0.0, 0.01),
        (0.85, 0.04, -0.04, 0.85, 0.0, 1.6, 0.85),
        (0.2, -0.26, 0.23, 0.22, 0.0, 1.6, 0.07),
        (-0.15, 0.28, 0.26, 0.24, 0.0, 0.44, 0.07))
BOUNDS = (-2.2, 0.0, 2.7, 10.0)  # x0, y0, x1, y1 of the attractor in map units


@lru_cache(maxsize=8)
def fern_points(count, seed=0, maps=MAPS):
    """`count` points of the chaos game for `maps`, in the order they land, as
    `(x, y, k)`: map units (y up, the stem's base at the origin) and the index
    of the map that placed it. The same `seed` gives the same points."""
    rnd = random.Random(seed)
    weights = [m[6] for m in maps]
    picks = rnd.choices(range(len(maps)), weights=weights, k=count)
    x = y = 0.0
    out = []
    for k in picks:
        a, b, c, d, e, f, _ = maps[k]
        x, y = a * x + b * y + e, c * x + d * y + f
        out.append((x, y, k))
    return tuple(out)


def fern_box(cx, base, height):
    """The (x, y, w, h) a fern `height` px tall, stem base at (cx, base), fills."""
    x0, y0, x1, y1 = BOUNDS
    s = height / (y1 - y0)
    return cx + x0 * s, base - height, (x1 - x0) * s, height


def draw_fern(cv, points, cx, base, height, colors=(demo.TEAL,), size=None):
    """Plot `points` (from `fern_points`, or any prefix of them, so the fern
    can grow frame by frame) as a fern `height` px tall whose stem base sits
    at (cx, base). Point i takes `colors[k % len(colors)]` for the map k that
    placed it. Plotted at the canvas's own pixel density (`size` overrides).
    Returns the Box it fills."""
    x0, y0, x1, y1 = BOUNDS
    bx, by, bw, bh = fern_box(cx, base, height)
    s = size or max(1e-6, cv.scale_factor())
    pw, ph = max(1, round(bw * s)), max(1, round(bh * s))
    sx, sy = (pw - 1) / (x1 - x0), (ph - 1) / (y1 - y0)
    pil = PILImage.new('RGBA', (pw, ph), (0, 0, 0, 0))
    pen = ImageDraw.Draw(pil)
    rgb = [tuple(round(v * 255) for v in vb.canvas.rgba(c)) for c in colors]
    buckets = [[] for _ in rgb]
    for x, y, k in points:
        buckets[k % len(rgb)].append(((x - x0) * sx, (y1 - y) * sy))
    for col, pts in zip(rgb, buckets):
        if pts:
            pen.point(pts, fill=col)
    cv.image(vb.canvas.Image.from_pil(pil), bx, by, bw, bh)
    return vb.Box(bx, by, bw, bh)


TOTAL = 90000


def draw(n, cv):
    pts = fern_points(TOTAL, seed=3)
    p = demo.phase(n, 0.2, 2.6)
    shown = max(1, round(TOTAL * p ** 2.2))  # a few lone hops first, then the dust pours in
    cx, base, height = demo.W / 2, demo.H - 30, demo.H - 70
    box = draw_fern(cv, pts[:shown], cx, base, height, colors=(demo.MUTED, demo.TEAL, demo.ACCENT, demo.ACCENT))
    # The travelling point, so the early frames show where the dust comes from.
    x0, y0, x1, y1 = BOUNDS
    x, y, _ = pts[shown - 1]
    demo.dot(cv, box.x + (x - x0) / (x1 - x0) * box.w, box.y + (y1 - y) / (y1 - y0) * box.h, r=5,
             color=demo.INK, alpha=1 - demo.phase(n, 2.2, 2.7))
    cv.mark('fern', *box)


CAPABILITY = Capability(
    id='barnsley-fern',
    name='Barnsley fern',
    family='particles',
    group='Fractals',
    aliases=('IFS fern', 'iterated function system', 'chaos game fern'),
    definition='A dot jumps around at random under a few stretch-and-shift rules, and the trail of '
               'every spot it lands on fills in, speck by speck, the shape of a fern frond.',
    phrasings=('a fern that builds itself out of thousands of tiny random dots',
               'the fractal fern made by plotting random points',
               'grow a leaf out of scattered particles that settle into a fern shape'),
    related=('l-system-plant', 'recursive-tree', 'diffusion-limited-aggregation', 'voronoi-relaxation',
             'falling-leaves', 'domino-toppling'),
    api=('videobuilder.capabilities.particles.barnsley_fern.draw_fern',
         'videobuilder.capabilities.particles.barnsley_fern.fern_points'),
    demo=lambda: demo.film(draw),
)

"""Pucker and bloat: a shape's corners and the sides between them are pushed
opposite ways about its centre -- pucker throws the corners out and sucks the
sides in to a spiky star; bloat pulls the corners in and swells the sides out
to round petals."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GAIN = 2.0  # how much further the sides travel than the corners


def pucker_bloat_segments(points, amount, center=None, gain=GAIN):
    """The closed polygon `points` distorted by `amount`, as cubic Bezier
    segments `(p0, c1, c2, p3)`, one per side. Each side starts as a straight
    cubic (handles at its thirds); then every corner is scaled about `center`
    (default: the mean of the corners) by `1 - amount` and every handle by
    `1 + gain * amount`. `amount` < 0 puckers (corners out, sides pinched in),
    > 0 bloats (corners in, sides puffed out), 0 leaves the polygon as it is."""
    n = len(points)
    cx, cy = center or (sum(x for x, _ in points) / n, sum(y for _, y in points) / n)

    def push(p, k):
        return cx + (p[0] - cx) * k, cy + (p[1] - cy) * k

    corner, handle = 1 - amount, 1 + gain * amount
    out = []
    for i, a in enumerate(points):
        b = points[(i + 1) % n]
        h1 = (a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3)
        h2 = (a[0] + 2 * (b[0] - a[0]) / 3, a[1] + 2 * (b[1] - a[1]) / 3)
        out.append((push(a, corner), push(h1, handle), push(h2, handle), push(b, corner)))
    return out


def pucker_bloat(points, amount, center=None, gain=GAIN, steps=24):
    """The closed polygon `points` puckered (`amount` < 0) or bloated (> 0),
    flattened to a closed point list of `steps` points per side, ready for
    `videobuilder.paths.draw` or any other point-list tool. See
    `pucker_bloat_segments` for the geometry."""
    out = []
    for p0, c1, c2, p3 in pucker_bloat_segments(points, amount, center, gain):
        for s in range(steps):
            t = s / steps
            u = 1 - t
            w0, w1, w2, w3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
            out.append((w0 * p0[0] + w1 * c1[0] + w2 * c2[0] + w3 * p3[0],
                        w0 * p0[1] + w1 * c1[1] + w2 * c2[1] + w3 * p3[1]))
    return out


def regular_polygon(cx, cy, r, sides, rotation=-math.pi / 2):
    """The corners of a regular polygon centred at (cx, cy), radius `r`, the
    first corner at `rotation` (default: straight up)."""
    return [(cx + r * math.cos(rotation + 2 * math.pi * i / sides),
             cy + r * math.sin(rotation + 2 * math.pi * i / sides)) for i in range(sides)]


PUCKER, BLOAT = -0.3, 0.4


def amount_at(n):
    """The demo's amount at frame `n`: hold the hexagon, pucker it, swing
    through the hexagon into a bloat, and hold there."""
    ease = vb.ease.ease_in_out_quart
    if n / demo.FPS < 1.35:
        return PUCKER * ease(demo.phase(n, 0.3, 1.1))
    return PUCKER + (BLOAT - PUCKER) * ease(demo.phase(n, 1.35, 2.5))


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 18, 115
    hexagon = regular_polygon(cx, cy, r, 6)
    amount = amount_at(n)
    for x, y in hexagon:  # faint spokes: the directions corners and sides are pushed along
        dx, dy = x - cx, y - cy
        cv.line(cx + dx * 0.3, cy + dy * 0.3, cx + dx * 1.75, cy + dy * 1.75, demo.LINE, width=2)
    shape = pucker_bloat(hexagon, amount)
    vb.paths.draw(cv, shape, demo.TEAL, fill=True, alpha=0.35)
    vb.paths.draw(cv, shape, demo.ACCENT, width=4, closed=True)
    for p0, *_ in pucker_bloat_segments(hexagon, amount):
        demo.dot(cv, *p0, r=6, color=demo.INK)
    xs, ys = [x for x, _ in shape], [y for _, y in shape]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    label = 'PUCKER' if amount < -0.05 else 'BLOAT' if amount > 0.05 else ''
    if label:
        demo.word(cv, label, cx, demo.H - 34, size=26, color=demo.MUTED, font=demo.mono(26, 700))


CAPABILITY = Capability(
    id='pucker-and-bloat',
    name='Pucker and bloat',
    family='shapes',
    group='Lines & strokes',
    aliases=('pinch and bulge', 'pinch bloat distortion', 'pucker & bloat'),
    definition='A shape distortion that drives its corners and its sides in opposite directions, '
               'so a polygon either sharpens into a pinched star or swells into rounded petals.',
    phrasings=('pinch the sides of the hexagon in so it turns into a spiky star',
               'puff the shape out into a flower with round petals',
               'make the polygon go starry and then blobby'),
    related=('twist-deformer', 'shape-morph-loader', 'taper-deformer', 'rubber-band-overscroll',
             'squash-on-tap', 'squash-and-stretch'),
    api=('videobuilder.capabilities.shapes.pucker_and_bloat.pucker_bloat',
         'videobuilder.capabilities.shapes.pucker_and_bloat.pucker_bloat_segments',
         'videobuilder.capabilities.shapes.pucker_and_bloat.regular_polygon'),
    demo=lambda: demo.film(draw),
)

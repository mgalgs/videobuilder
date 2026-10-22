"""Shape morph: videobuilder already has it as `paths.morph` (two outlines
resampled to match point for point, then interpolated) drawn with
`paths.draw`, so this entry only names it and demos it."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique

CX, CY, R = demo.W / 2, demo.H / 2, 150


def _circle(r=R, n=96):
    return [(CX + r * math.cos(2 * math.pi * i / n - math.pi / 2),
             CY + r * math.sin(2 * math.pi * i / n - math.pi / 2)) for i in range(n)]


def _star(r=R * 1.12, inner=0.45, points=5):
    return [(CX + r * (1 if i % 2 == 0 else inner) * math.cos(math.pi * i / points - math.pi / 2),
             CY + r * (1 if i % 2 == 0 else inner) * math.sin(math.pi * i / points - math.pi / 2))
            for i in range(2 * points)]


def _square(s=R * 0.9):
    return [(CX - s, CY - s), (CX + s, CY - s), (CX + s, CY + s), (CX - s, CY + s)]


def _mix(c0, c1, t):
    a, b = vb.canvas.rgba(c0), vb.canvas.rgba(c1)
    return tuple(round(255 * (x + (y - x) * t)) for x, y in zip(a[:3], b[:3]))


# (outline, colour) stops, and the (start, end) seconds of each morph between neighbours
STOPS = ((_circle(), demo.ACCENT), (_star(), demo.TEAL), (_square(), '#e8b04a'))
MOVES = ((0.4, 1.3), (1.75, 2.65))


def draw(n, cv):
    shape, color = STOPS[0]
    for (a, ca), (b, cb), (s, e) in zip(STOPS, STOPS[1:], MOVES):
        p = demo.phase(n, s, e)
        if p > 0:
            t = vb.ease_in_out_quart(p)
            shape, color = paths.morph(a, b, t, closed=True, n=240), _mix(ca, cb, t)
    paths.draw(cv, shape, color, fill=True)
    xs, ys = [x for x, _ in shape], [y for _, y in shape]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='shape-morph',
    name='Shape morph',
    family='transitions',
    group='Organic and Fluid',
    aliases=('morph', 'shape tween', 'path morph', 'shape interpolation'),
    definition='One outline flows continuously into a different outline, its edges sliding into the new '
               'shape rather than cutting or fading between the two.',
    phrasings=('turn the circle into a star smoothly instead of swapping them',
               'have one shape melt into the next',
               'blend this icon into that one without a cut'),
    related=('particle-morph', 'text-to-shape-morph', 'letter-morph', 'morphing-shape-ident',
             'chart-type-morph', 'shape-morph-loader'),
    api=('videobuilder.paths.morph', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)

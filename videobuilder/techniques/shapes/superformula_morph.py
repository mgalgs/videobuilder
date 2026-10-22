"""Superformula Morph: one closed outline drawn from the superformula (a
polar equation with a symmetry count `m` and three exponents `n1`, `n2`,
`n3`), its parameters tweened so the shape flows between polygons, stars
and petals without ever being redrawn."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def superformula(phi, m, n1, n2, n3, a=1.0, b=1.0):
    """The superformula's radius at angle `phi` (radians): `m` sets the
    rotational symmetry, `n1` how pinched (small) or swollen (large) the
    outline is, `n2`/`n3` how sharp its corners are. A fractional `m` blends
    the two neighbouring whole-number shapes, so the curve always closes."""
    lo = math.floor(m)
    if m != lo:
        r0, r1 = (superformula(phi, k, n1, n2, n3, a, b) for k in (lo, lo + 1))
        return r0 + (r1 - r0) * (m - lo)
    t = m * phi / 4
    s = abs(math.cos(t) / a) ** n2 + abs(math.sin(t) / b) ** n3
    return s ** (-1 / n1) if s > 1e-12 else 0.0


def superformula_points(cx, cy, radius, m, n1, n2, n3, a=1.0, b=1.0, rotation=0.0, n=360):
    """The superformula as a closed point list of `n` points centred at
    (cx, cy), scaled so its farthest point sits `radius` px out, turned by
    `rotation` radians (0: a lobe points straight up). Draw it with
    `vb.paths.draw(cv, pts, color, fill=True)`."""
    angles = [2 * math.pi * i / n for i in range(n)]
    rs = [superformula(phi, m, n1, n2, n3, a, b) for phi in angles]
    k = radius / (max(rs) or 1.0)
    turn = rotation - math.pi / 2
    return [(cx + r * k * math.cos(phi + turn), cy + r * k * math.sin(phi + turn)) for phi, r in zip(angles, rs)]


def superformula_morph(shapes, p, ease=vb.ease_in_out_quart):
    """The parameters `(m, n1, n2, n3)` at progress `p` (0 -> 1) through the
    keyframes `shapes` (a list of such tuples, at least two), each leg taking
    an equal share of `p` and eased by `ease`. `m` moves linearly, the
    exponents geometrically (they span 0.2 to 20, where equal ratios look
    like equal steps). Feed the result to `superformula_points`."""
    legs = len(shapes) - 1
    u = vb.clamp01(p) * legs
    i = min(int(u), legs - 1)
    t = ease(u - i)
    (m0, *e0), (m1, *e1) = shapes[i], shapes[i + 1]
    return (m0 + (m1 - m0) * t, *(vb.log_lerp(x0, x1, t) for x0, x1 in zip(e0, e1)))


# A pinched hexagon, a six-armed star, a three-lobed bloom and a starfish.
SHAPES = ((6, 1.0, 1.0, 1.0), (6, 1.5, 6.0, 6.0), (3, 4.5, 10.0, 10.0), (5, 2.0, 7.0, 7.0))


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 22, 190
    # Each shape holds a beat, then the next leg morphs: hold, move, hold, move ...
    beats = len(SHAPES) - 1
    u = demo.phase(n, 0.2, 2.8) * beats
    i = min(int(u), beats - 1)
    leg = vb.clamp01(((u - i) - 0.2) / 0.8)
    params = superformula_morph(SHAPES, (i + leg) / beats)
    pts = superformula_points(cx, cy, r, *params, rotation=0.25 * demo.phase(n, 0.0, 3.0))
    vb.paths.draw(cv, pts, demo.ACCENT, fill=True)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    m, n1, n2, n3 = params
    demo.word(cv, f'm {m:4.1f}   n1 {n1:5.2f}   n2 {n2:5.2f}   n3 {n3:5.2f}', demo.W / 2, demo.H - 34,
              color=demo.MUTED, font=demo.mono(20, 500))


TECHNIQUE = Technique(
    id='superformula-morph',
    name='Superformula morph',
    family='shapes',
    group='Shape morphing',
    aliases=('Gielis curve morph', 'superformula shape', 'superformula'),
    definition='A single closed outline built from one polar equation reshapes itself as the equation\'s '
               'numbers change, flowing from polygon to star to petals.',
    phrasings=('a blob that keeps turning into stars and flowers',
               'one shape that smoothly mutates between a hexagon, a star and a flower',
               'animate the superformula so the outline grows points and petals'),
    related=('shape-morph', 'koch-snowflake', 'projection-morph', 'julia-set-morph', 'morphing-shape-ident',
             'hilbert-curve'),
    api=('videobuilder.techniques.shapes.superformula_morph.superformula_morph',
         'videobuilder.techniques.shapes.superformula_morph.superformula_points',
         'videobuilder.techniques.shapes.superformula_morph.superformula'),
    demo=lambda: demo.film(draw),
)

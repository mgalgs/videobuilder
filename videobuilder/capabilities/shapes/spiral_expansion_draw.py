"""Spiral Expansion Draw: a spiral line is drawn from its centre outward, a
pen tip tracing turn after turn until the whole curve stands."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def spiral_points(cx, cy, radius, turns=4.0, inner=0.02, kind='log', start=0.0, clockwise=True, steps=90):
    """The points of a spiral centred at (cx, cy), from the centre out to
    `radius` across `turns` full turns, `steps` points per turn. `kind='log'`
    widens each turn by the same ratio (a shell or golden-spiral look), starting
    at `inner * radius`; `kind='linear'` widens it by the same distance (an
    Archimedean spiral, evenly spaced rings). `start` is the angle in radians
    of the outer end."""
    n = max(2, round(turns * steps))
    sweep = turns * 2 * math.pi
    sign = 1 if clockwise else -1
    out = []
    for i in range(n + 1):
        t = i / n
        r = radius * (inner ** (1 - t) if kind == 'log' else t)
        a = start + sign * (t - 1) * sweep
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def draw_spiral_expansion(cv, cx, cy, radius, p, color, width=6, by='length', tip=None, tip_r=None, alpha=1.0,
                          **kw):
    """Draw the spiral at (cx, cy) grown to progress `p` (0 -> 1) from its
    centre outward. `by='length'` moves the pen at a steady speed along the
    curve; `by='turns'` reveals an equal share of turns per unit of `p`, so the
    outer, longer turns sweep faster. `tip`: a colour to mark the pen's head
    with a dot (radius `tip_r`, default `1.6 * width`) while it is drawing.
    `kw` goes to `spiral_points`. Returns the drawn point list."""
    pts = spiral_points(cx, cy, radius, **kw)
    p = vb.clamp01(p)
    if by != 'turns':
        part = vb.paths.reveal(pts, p)
    else:
        k = p * (len(pts) - 1)
        i = int(k)
        part = pts[:i + 1]
        if i < len(pts) - 1 and k > i:
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            part.append((x0 + (x1 - x0) * (k - i), y0 + (y1 - y0) * (k - i)))
    vb.paths.draw(cv, part, color, width=width, alpha=alpha)
    if tip and part and 0 < p < 1:
        demo.dot(cv, *part[-1], r=tip_r or width * 1.6, color=tip, alpha=alpha)
    return part


def draw(n, cv):
    p = demo.phase(n, 0.25, 2.55)
    p = vb.ease_in_out_quart(p) * 0.35 + p * 0.65  # a gentle start and landing, mostly steady
    cx, cy, r = demo.W / 2, demo.H / 2, demo.H * 0.4
    draw_spiral_expansion(cv, cx, cy, r, p, demo.INK, width=demo.H / 120, turns=3.6, inner=0.03,
                          start=-math.pi / 2, tip=demo.ACCENT)
    cv.mark('spiral', cx - r, cy - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='spiral-expansion-draw',
    name='Spiral expansion draw',
    family='shapes',
    group='Geometric motion',
    aliases=('golden spiral draw', 'Fibonacci spiral reveal', 'logarithmic spiral', 'spiral draw-on'),
    definition='A single line starts at a centre point and winds outward, laying down one widening turn '
               'after another until the whole spiral is drawn.',
    phrasings=('draw a spiral that grows out from the middle',
               'a line coiling outward like a snail shell being sketched',
               'animate a golden spiral drawing itself turn by turn'),
    related=('spiral-wipe', 'spiral-bloom', 'dragon-curve', 'chord-diagram-draw', 'squircle-morph',
             'phyllotaxis'),
    api=('videobuilder.techniques.shapes.spiral_expansion_draw.draw_spiral_expansion',
         'videobuilder.techniques.shapes.spiral_expansion_draw.spiral_points'),
    demo=lambda: demo.film(draw),
)

"""Radial Repeater: one shape copied evenly around a centre, the copies
animated together (the ring spins, swells, and each copy turns in place) so
the whole arrangement moves as one pattern."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def radial_repeat(cv, cx, cy, count, draw_one, radius=0.0, rotation=0.0, spin=0.0):
    """Draw `count` copies of a shape spaced evenly around (cx, cy).

    `draw_one(cv, i)` draws copy `i` at the origin, its +x axis pointing
    away from the centre; it is called with the canvas moved to the copy's
    place, `radius` px out at angle `rotation + i * 2pi / count` (radians,
    clockwise from 3 o'clock), and turned a further `spin` radians about its
    own centre. Animate `radius`, `rotation` and `spin` (or vary the copy by
    `i` inside `draw_one`) to make the ring burst, turn or pulse."""
    c = cv.ctx
    for i in range(count):
        a = rotation + i * 2 * math.pi / count
        c.save()
        c.translate(cx + radius * math.cos(a), cy + radius * math.sin(a))
        c.rotate(a + spin)
        draw_one(cv, i)
        c.restore()


def draw(n, cv):
    cx, cy, count = demo.W / 2, demo.H / 2, 16
    burst = vb.ease_out_back(demo.phase(n, 0.15, 0.95))           # the ring blasts out from the centre
    turn = vb.ease_in_out_quart(demo.phase(n, 1.6, 2.6))         # each dash turns to lie along the ring
    t = n / demo.FPS
    radius = 20 + 150 * burst + 10 * math.sin(t * 2 * math.pi * 1.5) * (1 - turn)
    length, thick = 16 + 44 * burst * (1 - 0.35 * turn), 16

    def dash(cv, i):
        cv.rect(-length / 2, -thick / 2, length, thick, demo.ACCENT if i % 2 else demo.TEAL,
                radius=thick / 2, alpha=vb.clamp01(burst * 1.5))

    radial_repeat(cv, cx, cy, count, dash, radius=radius, rotation=t * 0.9 - 0.5 * math.pi,
                  spin=turn * math.pi / 2)
    r = radius + length / 2
    cv.mark('ring', cx - r, cy - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='radial-repeater',
    name='Radial repeater',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('radial duplication', 'circular copies', 'polar array', 'radial array'),
    definition='Many copies of a single shape sit at equal steps around a centre point and move together, '
               'so the ring spins, swells or reshapes as one pattern.',
    phrasings=('a ring of dashes that bursts out and spins',
               'repeat this shape in a circle around the middle',
               'copies of the icon arranged like clock marks, rotating'),
    related=('sound-reactive-radial-shape', 'radial-stagger', 'circle-packing', 'pie-sweep', 'circle-pop',
             'rotating-polygon-loop'),
    api=('videobuilder.capabilities.shapes.radial_repeater.radial_repeat',),
    demo=lambda: demo.film(draw),
)

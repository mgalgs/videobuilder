"""Circle pop: a dot that grows out of nothing, swells a little past its size
and settles back -- the overshoot scale-in, applied to a circle."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def circle_pop(cv, cx, cy, r, p, color, alpha=1.0, ease=vb.ease_out_back):
    """Draw a circle of rest radius `r` centred at (cx, cy), popped in to
    progress `p` (0 -> 1): its radius runs from 0 through a small overshoot
    to `r` along `ease`. Nothing is drawn before it starts. Returns the radius drawn."""
    radius = r * ease(vb.clamp01(p))
    if radius > 0:
        cv.sector(cx, cy, radius, 0, 2 * math.pi, color, alpha=alpha)
    return radius


def draw(n, cv):
    r, y, gap = 80, demo.H / 2, 260
    for i, color in enumerate((demo.ACCENT, demo.TEAL, demo.ACCENT)):
        cx = demo.W / 2 + (i - 1) * gap
        cv.outline(cx - r, y - r, 2 * r, 2 * r, demo.LINE, width=2, radius=r, alpha=0.6)  # its rest size
        start = 0.4 + 0.35 * i
        radius = circle_pop(cv, cx, y, r, demo.phase(n, start, start + 0.6), color)
        if radius > 0:
            cv.mark(f'circle{i}', cx - radius, y - radius, 2 * radius, 2 * radius)


CAPABILITY = Capability(
    id='circle-pop',
    name='Circle pop',
    family='shapes',
    group='Bounce & pop',
    aliases=('bubble pop-in', 'dot pop', 'scale pop'),
    definition='A circle grows from a point, briefly swells beyond its final size, then shrinks back '
               'and settles there.',
    phrasings=('make the dot pop into existence with a little bounce',
               'have the circles appear like bubbles popping up',
               'scale the circle in from nothing with some overshoot'),
    related=('radio-dot-scale', 'bubbles', 'circle-packing', 'squircle-morph', 'character-scale-in',
             'halftone-dot-scaling'),
    api=('videobuilder.capabilities.shapes.circle_pop.circle_pop', 'videobuilder.ease_out_back'),
    demo=lambda: demo.film(draw),
)

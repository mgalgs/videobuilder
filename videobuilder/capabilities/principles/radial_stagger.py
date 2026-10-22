"""Radial Stagger: a field of elements animates in a wave that starts at one
point and spreads outward, each element's start delayed by its distance
from that point."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def radial_stagger(p, x, y, cx, cy, reach, spread=0.6):
    """The local progress (0 -> 1) at overall progress `p` of an element at
    (x, y), for a wave leaving (cx, cy). An element `reach` or more away
    starts `spread` of the way through; nearer ones start in proportion to
    their distance. Each element's own move takes the remaining `1 - spread`,
    so the farthest one finishes exactly at `p = 1`. Ease the result as usual."""
    d = min(1.0, math.hypot(x - cx, y - cy) / reach) if reach > 0 else 0.0
    return vb.clamp01((p - spread * d) / (1 - spread))


COLS, ROWS, GAP = 15, 9, 50


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    x0, y0 = cx - (COLS - 1) * GAP / 2, cy - (ROWS - 1) * GAP / 2
    reach = math.hypot(x0 - cx, y0 - cy)
    p = demo.phase(n, 0.3, 2.3)
    for j in range(ROWS):
        for i in range(COLS):
            x, y = x0 + i * GAP, y0 + j * GAP
            q = radial_stagger(p, x, y, cx, cy, reach, spread=0.7)
            if q <= 0:
                demo.dot(cv, x, y, 2, color=demo.LINE)  # where each dot will appear
                continue
            color = demo.ACCENT if q < 1 else demo.TEAL
            demo.dot(cv, x, y, 16 * vb.ease_out_back(q), color=color)
    demo.dot(cv, cx, cy, 5, color=demo.INK)
    cv.mark('origin', cx - 5, cy - 5, 10, 10)


CAPABILITY = Capability(
    id='radial-stagger',
    name='Radial Stagger',
    family='principles',
    group='Stagger',
    aliases=('radial cascade', 'ripple stagger', 'stagger from center', 'distance-based stagger'),
    definition='A group of elements animates one after another in rings spreading out from a single point, '
               'each one delayed by how far it sits from that point.',
    phrasings=('make the dots pop in from the middle outward like a ripple',
               'stagger the grid so it spreads out from the center',
               'the items should appear in a wave radiating from one spot'),
    related=('sound-reactive-radial-shape', 'spinner-ring', 'orbital-pulse', 'rotating-rings', 'radial-repeater',
             'circle-packing'),
    api=('videobuilder.capabilities.principles.radial_stagger.radial_stagger',),
    demo=lambda: demo.film(draw),
)

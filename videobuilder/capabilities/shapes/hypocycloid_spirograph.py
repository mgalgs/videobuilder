"""Spirograph: a small wheel rolls around the inside of a fixed ring while a
pen set in the wheel traces a looping, petalled curve (a hypotrochoid) that
closes on itself once the wheel has gone round enough times."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def turns(ring, wheel):
    """How many times the wheel's centre circles the ring before the curve
    closes: `wheel / gcd(ring, wheel)` (both whole numbers of teeth)."""
    return wheel // math.gcd(ring, wheel)


def spirograph(cx, cy, ring, wheel, pen, p=1.0, steps=2400):
    """The curve traced by a pen `pen` px from the centre of a wheel of radius
    `wheel` rolling inside a ring of radius `ring` centred at (cx, cy), up to
    progress `p` (0 -> 1 is the whole closed figure). Pass whole numbers for
    `ring` and `wheel` so the figure closes. Returns `(points, (wx, wy, a))`:
    the traced point list, and the wheel's centre and own rotation at `p`,
    for drawing the wheel itself."""
    total = 2 * math.pi * turns(ring, wheel)
    k = (ring - wheel) / wheel
    end = total * vb.clamp01(p)
    count = max(1, round(steps * vb.clamp01(p)))
    pts = []
    for i in range(count + 1):
        t = end * i / count
        pts.append((cx + (ring - wheel) * math.cos(t) + pen * math.cos(k * t),
                    cy + (ring - wheel) * math.sin(t) - pen * math.sin(k * t)))
    wx, wy = cx + (ring - wheel) * math.cos(end), cy + (ring - wheel) * math.sin(end)
    return pts, (wx, wy, -k * end)


def draw_spirograph(cv, cx, cy, ring, wheel, pen, p, color, width=3, gear=demo.TEAL, guide=demo.MUTED,
                    gear_alpha=1.0):
    """Draw the figure at progress `p`: the trace in `color`, then the fixed
    ring in `guide` and the rolling wheel, pen arm and pen tip in `gear`, all
    at `gear_alpha` (0 hides them, leaving the bare figure). Returns the Box
    of the full ring."""
    pts, (wx, wy, a) = spirograph(cx, cy, ring, wheel, pen, p)
    vb.paths.draw(cv, pts, color, width=width)
    alpha = gear_alpha
    if alpha > 0:
        cv.arc(cx, cy, ring, 0, 2 * math.pi, guide, width=3, alpha=0.6 * alpha)
        cv.arc(wx, wy, wheel, 0, 2 * math.pi, gear, width=3, alpha=alpha)
        for s in range(6):  # spokes, so the wheel is seen to turn as it rolls
            sa = a + s * math.pi / 3
            cv.line(wx, wy, wx + wheel * math.cos(sa), wy + wheel * math.sin(sa), gear, width=1.5,
                    alpha=0.35 * alpha)
        px, py = pts[-1]
        cv.line(wx, wy, px, py, gear, width=3, alpha=alpha)
        demo.dot(cv, wx, wy, 7, color=gear, alpha=alpha)
        demo.dot(cv, px, py, 11, color=color, alpha=alpha)
    return vb.Box(cx - ring, cy - ring, 2 * ring, 2 * ring)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.4))
    lift = demo.phase(n, 2.4, 2.8)  # the gear lifts away once the figure closes
    box = draw_spirograph(cv, demo.W / 2, demo.H / 2, 224, 140, 112, p, demo.ACCENT, gear_alpha=1 - lift)
    cv.mark('figure', *box)


CAPABILITY = Capability(
    id='hypocycloid-spirograph',
    name='Spirograph',
    family='shapes',
    group='Geometric motion',
    aliases=('hypotrochoid', 'hypocycloid', 'spirograph drawing', 'rolling circle curve'),
    definition='A pen fixed in a small wheel rolling round the inside of a larger ring draws a looping, '
               'petalled line that grows until the pattern closes on itself.',
    phrasings=('draw one of those spirograph flower patterns being traced out',
               'a gear rolling inside a circle drawing a looping rosette',
               'animate the line of a spirograph toy building up'),
    related=('highlight-circle-draw', 'cycle-diagram-rotation', 'radial-stagger', 'rotating-polygon-loop',
             'radar-chart-fill', 'cymatics'),
    api=('videobuilder.capabilities.shapes.hypocycloid_spirograph.draw_spirograph',
         'videobuilder.capabilities.shapes.hypocycloid_spirograph.spirograph'),
    demo=lambda: demo.film(draw),
)

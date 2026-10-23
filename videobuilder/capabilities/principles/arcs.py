"""Arcs: a thing moving from one place to another travels a curved path
rather than a ruler-straight line, the way a swung arm or a turning head
does. `arc_point` gives the position along a circular arc between two points."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def arc_point(x0, y0, x1, y1, p, bend=0.3):
    """The point at progress `p` (0 -> 1, clamped) along a circular arc from
    (x0, y0) to (x1, y1), at constant speed along the arc. `bend` is how far
    the arc's middle sits off the straight line, as a fraction of the
    distance between the ends: positive bulges to the left of the direction
    of travel (upward for a left-to-right move on screen), negative to the
    right, 0 is the straight line. Ease `p` first for an eased move."""
    p = vb.clamp01(p)
    dx, dy = x1 - x0, y1 - y0
    chord = math.hypot(dx, dy)
    if chord == 0 or bend == 0:
        return x0 + dx * p, y0 + dy * p
    nx, ny = dy / chord, -dx / chord  # unit normal to the left of travel (y grows downward)
    if bend < 0:
        nx, ny, bend = -nx, -ny, -bend
    s = bend * chord                  # the sagitta: how far the arc's middle is off the chord
    r = (chord * chord / 4 + s * s) / (2 * s)
    cx, cy = (x0 + x1) / 2 - nx * (r - s), (y0 + y1) / 2 - ny * (r - s)
    a0 = math.atan2(y0 - cy, x0 - cx)
    sweep = 4 * math.atan(2 * bend)
    mid = a0 + sweep / 2              # turn whichever way passes through the bulge
    if math.cos(mid) * nx + math.sin(mid) * ny < 0:
        sweep = -sweep
    a = a0 + sweep * p
    return cx + r * math.cos(a), cy + r * math.sin(a)


def arc_path(x0, y0, x1, y1, bend=0.3, n=64):
    """The whole arc of `arc_point` as a point list of `n + 1` points, for
    `vb.paths.draw` or `vb.paths.reveal`."""
    return [arc_point(x0, y0, x1, y1, i / n, bend) for i in range(n + 1)]


def _there_and_back(n):
    return vb.ease_in_out_quart(demo.phase(n, 0.35, 1.45)) * (1 - vb.ease_in_out_quart(demo.phase(n, 1.75, 2.85)))


def draw(n, cv):
    # Wide across the frame, the baseline low enough that the arc's peak and
    # the dot below the baseline sit evenly about the middle.
    y = demo.H / 2 + 105
    x0, y0, x1, y1 = 140, y, demo.W - 140, y
    bend = 0.32
    # The straight line it doesn't take, faint and dotted, for contrast.
    steps = 40
    for i in range(0, steps + 1, 2):
        demo.dot(cv, x0 + (x1 - x0) * i / steps, y0, r=3, color=demo.MUTED, alpha=0.45)
    for x, y in ((x0, y0), (x1, y1)):
        demo.dot(cv, x, y, r=10, color=demo.MUTED, alpha=0.6)
    # There and back along the arc, eased, leaving onion-skin ghosts behind.
    p = _there_and_back(n)
    vb.paths.draw(cv, arc_path(x0, y0, x1, y1, bend), demo.TEAL, width=3, alpha=0.35)
    for k in range(1, 9):
        g = n - 2 * k
        if g < 0:
            break
        gx, gy = arc_point(x0, y0, x1, y1, _there_and_back(g), bend)
        demo.dot(cv, gx, gy, r=30, color=demo.ACCENT, alpha=0.32 * (1 - k / 9))
    x, y = arc_point(x0, y0, x1, y1, p, bend)
    demo.dot(cv, x, y, r=34)
    cv.mark('dot', x - 34, y - 34, 68, 68)


CAPABILITY = Capability(
    id='arcs',
    name='Arcs',
    family='principles',
    group='Classic principles',
    aliases=('arc motion', 'motion arcs', 'follow an arc'),
    definition='Movement from one point to another follows a gentle curve instead of a straight line, '
               'which makes it feel natural and alive rather than mechanical.',
    phrasings=('make it swing over in a curve instead of sliding straight across',
               'move it along a natural curved path',
               'the motion feels too robotic, give it some arc'),
    related=('bend-deformer', 'flight-arc', 'projectile-arc', 'path-follow-motion', 'arc-bend-morph',
             'wander-steering'),
    api=('videobuilder.capabilities.principles.arcs.arc_point',
         'videobuilder.capabilities.principles.arcs.arc_path'),
    demo=lambda: demo.film(draw),
)

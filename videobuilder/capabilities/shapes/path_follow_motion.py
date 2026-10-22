"""Path Follow Motion: an object travels along a drawn curve, its position
taken by arc length so the speed stays even, and it turns to face the way
the path is heading as it goes."""
import math
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def point_along(points, fraction, closed=False):
    """Where `fraction` (0..1, clamped; wrapped when `closed`) of the way
    along `points` by arc length is, as `(x, y, angle)`: `angle` is the
    heading of the path there in radians, clockwise from +x (canvas
    convention), so an item drawn pointing right can be turned by it."""
    pts = list(points) + ([points[0]] if closed else [])
    if len(pts) < 2:
        x, y = pts[0] if pts else (0.0, 0.0)
        return x, y, 0.0
    fraction = fraction % 1.0 if closed and fraction != 1 else vb.clamp01(fraction)
    hops = [math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
    target, acc = sum(hops) * fraction, 0.0
    for i, hop in enumerate(hops):
        if hop > 0 and (acc + hop >= target or i == len(hops) - 1):
            t = min(1.0, (target - acc) / hop)
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.atan2(y1 - y0, x1 - x0)
        acc += hop
    return pts[0][0], pts[0][1], 0.0


@contextmanager
def follow(cv, points, fraction, closed=False, orient=True, offset=0.0):
    """Draw inside this block about the origin, pointing along +x, and it
    lands `fraction` of the way along `points`, turned to the path's heading
    when `orient` (plus `offset` radians). Yields `(x, y, angle)`."""
    x, y, angle = point_along(points, fraction, closed)
    c = cv.ctx
    c.save()
    c.translate(x, y)
    if orient:
        c.rotate(angle + offset)
    try:
        yield x, y, angle
    finally:
        c.restore()


def cubic(p0, p1, p2, p3, steps=48):
    """A cubic Bezier from `p0` to `p3` (controls `p1`, `p2`) as a point list."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


W, H = demo.W, demo.H
PATH = (cubic((W * 0.10, H * 0.78), (W * 0.22, H * 0.05), (W * 0.40, H * 0.10), (W * 0.48, H * 0.50))
        + cubic((W * 0.48, H * 0.50), (W * 0.56, H * 0.92), (W * 0.78, H * 0.95), (W * 0.90, H * 0.24))[1:])
ARROW = [(46, 0), (-30, -30), (-16, 0), (-30, 30)]


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.7))
    vb.paths.draw(cv, PATH, demo.MUTED, width=4, alpha=0.35)
    vb.paths.draw(cv, vb.paths.reveal(PATH, p), demo.ACCENT, width=6, alpha=0.6)
    for end in (PATH[0], PATH[-1]):
        demo.dot(cv, *end, r=10, color=demo.MUTED)
    with follow(cv, PATH, p) as (x, y, a):
        # the shadow falls straight down the frame, whichever way the arrow points
        cv.shape_shadow(ARROW, dx=8 * math.sin(a), dy=8 * math.cos(a), blur=14, color=(0, 0, 0, 0.45))
        vb.paths.draw(cv, ARROW, demo.TEAL, fill=True)
    cv.mark('item', x - 46, y - 46, 92, 92)


CAPABILITY = Capability(
    id='path-follow-motion',
    name='Path follow motion',
    family='shapes',
    group='Lines & strokes',
    aliases=('motion path', 'follow path', 'orient along path', 'path animation'),
    definition='An object travels along a drawn curve, turning as it goes so it always points '
               'the way the curve is going.',
    phrasings=('make the arrow travel along this curvy line and turn with it',
               'have the plane fly along the dotted route, nose first',
               'animate the icon following a path instead of moving in a straight line'),
    related=('path-emitter', 'arcs', 'follow-through', 'player-movement-trail', 'text-on-a-path',
             'chain-follow-through'),
    api=('videobuilder.capabilities.shapes.path_follow_motion.follow',
         'videobuilder.capabilities.shapes.path_follow_motion.point_along',
         'videobuilder.capabilities.shapes.path_follow_motion.cubic'),
    demo=lambda: demo.film(draw),
)

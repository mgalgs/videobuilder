"""Zig-zag Distortion: a path's points pushed alternately to one side and the
other along its normal, so a smooth stroke becomes an even sawtooth whose
height and tooth count can animate."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _walker(points, closed):
    """A function arc length s -> ((x, y), (tx, ty)): the point that far along
    `points` and the unit tangent of the hop it lies on."""
    pts = list(points) + ([points[0]] if closed else [])
    hops = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        if d > 0:
            hops.append((x0, y0, (x1 - x0) / d, (y1 - y0) / d, d))

    def at(s):
        for x0, y0, tx, ty, d in hops:
            if s <= d:
                return (x0 + tx * s, y0 + ty * s), (tx, ty)
            s -= d
        x0, y0, tx, ty, d = hops[-1]
        return (x0 + tx * d, y0 + ty * d), (tx, ty)
    return at


def _wave(u):
    """A unit triangle wave over cycles `u`: 0 at 0, +1 at 1/4, -1 at 3/4."""
    f = (u - 0.25) % 1.0
    return 1 - 4 * f if f < 0.5 else 4 * f - 3


def zigzag(points, amplitude, ridges, closed=False, phase=0.0):
    """`points` (a `vb.paths` point list) zig-zagged: straight hops between
    corners pushed `amplitude` px out to either side of the path, alternating,
    `ridges` full teeth (one up, one down) along its length. Both may be
    animated per frame -- `amplitude` 0 gives the path back, and `ridges` may
    be fractional on an open path (a closed one rounds it so the wave meets
    itself). `phase` (in teeth) slides the teeth along the path. An open path
    keeps its own end points. Draw the result with `vb.paths.draw`."""
    pts = list(points)
    total = vb.paths.length(pts, closed)
    if len(pts) < 2 or total == 0 or ridges <= 0:
        return pts
    if closed:
        ridges = max(1, round(ridges))
    at = _walker(pts, closed)
    span = total / ridges  # arc length of one full tooth
    # the corners sit on the wave's peaks and troughs: u = 1/4 + j/2 (in teeth), u = s / span + phase
    j0 = math.ceil((phase - 0.25) * 2)
    stops = []
    j = j0
    while True:
        s = ((0.25 + j / 2) - phase) * span
        if s >= total - 1e-6:
            break
        if s > 1e-6:
            stops.append(s)
        j += 1
    if not closed:
        stops = [0.0] + stops + [total]
    out = []
    for s in stops:
        (x, y), (tx, ty) = at(s)
        # an open path's two end stops stay on the path, whatever ridges and phase leave the wave at there
        pinned = not closed and (s == 0.0 or s == total)
        push = 0.0 if pinned else amplitude * _wave(s / span + phase)
        out.append((x - ty * push, y + tx * push))
    return out


def draw(n, cv):
    y, x0, x1 = demo.H / 2, demo.W / 2 - 360, demo.W / 2 + 360
    grow = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.3))
    settle = vb.ease_in_out_quart(demo.phase(n, 1.7, 2.6))
    amp = 5 + 65 * grow - 44 * settle          # a faint crimp, a deep sawtooth, then a medium one
    teeth = 15 - 3 * settle                     # and the teeth widen as it settles
    line = zigzag([(x0, y), (x1, y)], amp, teeth)
    vb.paths.draw(cv, line, demo.ACCENT, width=5)
    for x in (x0, x1):
        demo.dot(cv, x, y, 7, color=demo.INK)
    cv.mark('stroke', x0, y - amp, x1 - x0, 2 * amp)


CAPABILITY = Capability(
    id='zig-zag-distortion',
    name='Zig-zag distortion',
    family='shapes',
    group='Lines & strokes',
    aliases=('zigzag path', 'sawtooth edge', 'crimp'),
    definition='A straight or curved stroke is bent into a row of sharp, evenly spaced teeth '
               'whose height and spacing can grow, shrink or shift over time.',
    phrasings=('turn the line into a zigzag and make the zigzag get bigger',
               'give the stroke a jagged sawtooth edge that animates',
               'crimp the path into sharp little peaks'),
    related=('zigzag-wipe', 'accordion-fold', 'perspective-tunnel-type', 'lens-distortion', 'dragon-curve',
             'morph-cut'),
    api=('videobuilder.capabilities.shapes.zig_zag_distortion.zigzag', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)

"""Line weave: straight threads strung between evenly spaced pins on two
rails, the first pin of one rail to the last of the other, so their crossings
trace a curve no single line contains; move a rail and the curve reshapes."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _at(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def weave(a0, a1, b0, b1, count):
    """The threads of a weave between rail `a0 -> a1` and rail `b0 -> b1`, as
    `count` segments `((x, y), (x, y))`: thread `i` runs from pin `i` on rail
    a to pin `i` on rail b, pins evenly spaced end to end. With the rails
    meeting at a corner (`a1 == b0`) the threads wrap a parabola into it."""
    out = []
    for i in range(count):
        t = i / (count - 1) if count > 1 else 0.5
        out.append((_at(a0, a1, t), _at(b0, b1, t)))
    return out


def draw_weave(cv, a0, a1, b0, b1, count, color, width=1.5, progress=1.0, spread=0.6, alpha=1.0):
    """Draw the `weave` between two rails onto `cv`. `progress` (0 -> 1)
    strings the threads in order, each drawing from its rail-a pin to its
    rail-b pin; `spread` is how much of the run threads overlap (0: one at a
    time, 1: all together). Re-call it each frame with moved rail ends to
    redraw the pattern. Returns the threads drawn, as from `weave`."""
    threads = weave(a0, a1, b0, b1, count)
    span = 1 - spread * (1 - 1 / max(count, 1))  # each thread's own share of the run
    for i, (p, q) in enumerate(threads):
        start = (1 - span) * i / max(count - 1, 1)
        k = vb.clamp01((progress - start) / span) if span > 0 else float(progress >= start)
        if k <= 0:
            continue
        cv.line(*p, *_at(p, q, k), color, width=width, alpha=alpha)
    return threads


def _rail(cv, a, b, pins):
    cv.line(*a, *b, demo.MUTED, width=2, alpha=0.6)
    for i in range(pins):
        demo.dot(cv, *_at(a, b, i / (pins - 1)), r=2.5, color=demo.ACCENT)


def draw(n, cv):
    cx, cy, arm, count = demo.W / 2, demo.H / 2, 220, 22
    strung = demo.phase(n, 0.2, 1.5)
    swing = demo.phase(n, 1.6, 2.8)
    swing = 0.5 - 0.5 * math.cos(math.pi * swing)
    # four arms from the centre; two of them swing round so every quadrant's angle changes
    angles = [0, math.pi / 2 + 0.55 * swing, math.pi, 3 * math.pi / 2 + 0.55 * swing]
    ends = [(cx + arm * math.cos(a), cy - arm * math.sin(a)) for a in angles]
    centre = (cx, cy)
    for i in range(4):
        a, b = ends[i], ends[(i + 1) % 4]
        color = demo.TEAL if i % 2 else demo.INK
        draw_weave(cv, a, centre, centre, b, count, color, width=1.2, progress=strung, alpha=0.85)
    for e in ends:
        _rail(cv, centre, e, count)
    cv.mark('weave', cx - arm, cy - arm, 2 * arm, 2 * arm)


CAPABILITY = Capability(
    id='line-weave',
    name='Line weave',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('string art', 'thread pattern', 'crossing lines pattern'),
    definition='Straight lines strung between matching points on two edges cross one another so densely '
               'that a smooth curve appears, and it bends as the edges move.',
    phrasings=('string art where straight threads make a curve',
               'lines stretched between two sides that weave into a curved shape',
               'a thread pattern that reshapes as its corners swing'),
    related=('streamlines', 'line-chart-draw-on', 'interlace-combing', 'speed-lines', 'stroke-draw-on',
             'line-to-polygon-transform'),
    api=('videobuilder.capabilities.shapes.line_weave.draw_weave',
         'videobuilder.capabilities.shapes.line_weave.weave'),
    demo=lambda: demo.film(draw),
)

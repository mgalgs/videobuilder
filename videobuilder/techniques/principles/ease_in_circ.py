"""Ease In Circ: an easing curve shaped like a quarter of a circle, barely
moving at first and then speeding up hard, so it leaves at full tilt."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_in_circ(x):
    """Progress `x` in [0, 1] -> eased progress along a quarter circle:
    `1 - sqrt(1 - x**2)`, flat at the start and vertical at the end."""
    x = vb.clamp01(x)
    return 1 - math.sqrt(1 - x * x)


START, END = 0.4, 2.2  # seconds the move runs
TRACK_Y, X0, X1 = 130, 140, demo.W - 140
GX, GY, GW, GH = demo.W / 2 - 170, demo.H - 60, 340, 220  # the graph: time across, progress up


def _graph_point(t):
    return GX + GW * t, GY - GH * ease_in_circ(t)


def draw(n, cv):
    t = demo.phase(n, START, END)
    p = ease_in_circ(t)

    # the track, with ghosts at even steps of time: their gaps widen as it speeds up
    demo.floor(cv, TRACK_Y + 50)
    for i in range(9):
        g = i / 8
        if g <= t:
            demo.dot(cv, X0 + (X1 - X0) * ease_in_circ(g), TRACK_Y + 50, 6, color=demo.MUTED)
    x = X0 + (X1 - X0) * p
    demo.dot(cv, x, TRACK_Y, 34)
    cv.mark('ball', x - 34, TRACK_Y - 34, 68, 68)

    # the curve, drawn in faintly and traced brightly up to now
    cv.line(GX, GY, GX + GW, GY, demo.LINE, width=2)
    cv.line(GX, GY, GX, GY - GH, demo.LINE, width=2)
    steps = 80
    for i in range(steps):
        a, b = i / steps, (i + 1) / steps
        lit = b <= t
        cv.line(*_graph_point(a), *_graph_point(b), demo.INK if lit else demo.MUTED,
                width=3 if lit else 2, alpha=1.0 if lit else 0.35)
    demo.dot(cv, *_graph_point(t), 8)


TECHNIQUE = Technique(
    id='ease-in-circ',
    name='Ease In Circ',
    family='principles',
    group='Easing',
    aliases=('circular in', 'easeInCirc', 'circ in'),
    definition='A move that creeps away from rest and then gathers speed sharply along a quarter-circle '
               'curve, so it is going fastest at the very end.',
    phrasings=('starts really slow and then shoots off at the end',
               'gathers speed and leaves the frame in a rush',
               'a slow wind-up that suddenly whips away'),
    related=('arcs', 'slow-in-and-slow-out', 'progress-ring', 'bend-deformer', 'pie-sweep',
             'smooth-scroll-inertia'),
    api=('videobuilder.techniques.principles.ease_in_circ.ease_in_circ',),
    demo=lambda: demo.film(draw),
)

"""Ease In-Out Sine: the gentlest symmetric ease, half a cosine wave -- the move
gathers speed softly, is quickest at the halfway point, and settles just as
softly."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_in_out_sine(x):
    """Progress `x` in [0, 1] -> eased progress along half a cosine wave:
    zero speed at both ends, fastest (pi/2 times linear) at 0.5."""
    return (1 - math.cos(math.pi * vb.clamp01(x))) / 2


START, END = 0.4, 2.6   # the move, in seconds
STEPS = 12              # evenly spaced moments sampled along the move


def draw(n, cv):
    x0, x1, y = 320, demo.W - 320, demo.H / 2 - 40
    t = demo.phase(n, START, END)
    p = ease_in_out_sine(t)
    cv.line(x0, y, x1, y, demo.LINE, width=3)
    for x in (x0, x1):
        cv.line(x, y - 18, x, y + 18, demo.MUTED, width=3)
    # Where the dot is at equal slices of time: packed at the ends, spread out mid-way.
    for k in range(STEPS + 1):
        s = k / STEPS
        if s <= t:
            demo.dot(cv, x0 + (x1 - x0) * ease_in_out_sine(s), y + 90, 7, color=demo.TEAL)
    # A plain clock underneath, running at constant speed, for comparison.
    cv.line(x0, y + 170, x1, y + 170, demo.LINE, width=3)
    cv.line(x0, y + 170, x0 + (x1 - x0) * t, y + 170, demo.MUTED, width=3)
    demo.dot(cv, x0 + (x1 - x0) * t, y + 170, 8, color=demo.INK)
    cx = x0 + (x1 - x0) * p
    demo.dot(cv, cx, y, 40)
    cv.mark('ball', cx - 40, y - 40, 80, 80)


TECHNIQUE = Technique(
    id='ease-in-out-sine',
    name='Ease In-Out Sine',
    family='principles',
    group='Easing',
    aliases=('easeInOutSine', 'sine in-out', 'sinusoidal ease in-out'),
    definition='A move that drifts off gently, is quickest right at its midpoint, and drifts to a stop '
               'just as gently, its speed rising and falling like a smooth wave.',
    phrasings=('glides across softly, slow at the start and the end',
               'a smooth, gentle ease in and out',
               'speeds up and slows down evenly, nothing abrupt'),
    related=('slow-in-and-slow-out', 'sine-wave-distortion', 'sine-wave-text', 'smooth-scroll-inertia',
             'wave-deformer', 'oscillation'),
    api=('videobuilder.techniques.principles.ease_in_out_sine.ease_in_out_sine',),
    demo=lambda: demo.film(draw),
)

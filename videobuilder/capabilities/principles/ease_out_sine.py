"""Ease Out Sine: the gentlest of the ease-out curves, a quarter sine wave that
leaves at a brisk pace and slows smoothly into its target with no overshoot."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_out_sine(x):
    """Progress `x` in [0, 1] -> eased progress: the first quarter of a sine
    wave, so it starts at its fastest and its speed falls smoothly to zero at 1."""
    return math.sin(vb.clamp01(x) * math.pi / 2)


START, END, SAMPLES = 0.4, 2.4, 13


def draw(n, cv):
    x0, x1, y = 260, demo.W - 260, demo.H / 2 - 40
    cv.line(x0, y, x1, y, demo.LINE, width=3)
    cv.line(x1, y - 26, x1, y + 26, demo.MUTED, width=3)  # the target
    p = demo.phase(n, START, END)
    # Where the dot was at evenly spaced moments: wide gaps early, bunching up near the end.
    for i in range(SAMPLES):
        t = i / (SAMPLES - 1)
        if t <= p:
            demo.dot(cv, x0 + (x1 - x0) * ease_out_sine(t), y + 120, 9, color=demo.TEAL)
    x = x0 + (x1 - x0) * ease_out_sine(p)
    demo.dot(cv, x, y, 46)
    cv.mark('dot', x - 46, y - 46, 92, 92)


CAPABILITY = Capability(
    id='ease-out-sine',
    name='Ease Out Sine',
    family='principles',
    group='Easing',
    aliases=('sine out', 'easeOutSine', 'ease out sinusoidal'),
    definition='A move that sets off at its quickest and then slows softly and evenly until it comes '
               'to rest on its target, following a quarter of a sine wave.',
    phrasings=('glides in and gently coasts to a stop',
               'slows down softly as it arrives',
               'a soft, subtle ease out with no overshoot'),
    related=('slow-in-and-slow-out', 'settle', 'smooth-scroll-inertia', 'asymmetric-fast-in-slow-out',
             'oscillation', 'sine-wave-text'),
    api=('videobuilder.capabilities.principles.ease_out_sine.ease_out_sine',),
    demo=lambda: demo.film(draw),
)

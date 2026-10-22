"""Ease In Sine: the gentlest of the ease-in curves, a quarter of a cosine
wave, so a move leaves its start softly and gathers speed up to the end."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

STEPS = 12  # equal slices of time, marked on the track so the widening spacing shows the pickup


def ease_in_sine(x):
    """Progress `x` in [0, 1] -> eased progress: `1 - cos(x * pi / 2)`, zero
    speed at the start and full speed at the end."""
    return 1 - math.cos(vb.clamp01(x) * math.pi / 2)


def draw(n, cv):
    t = demo.phase(n, 0.4, 2.4)
    x0, x1, y = 260, demo.W - 260, demo.H / 2 - 40
    cv.line(x0, y, x1, y, demo.LINE, width=3)
    for end in (x0, x1):
        cv.line(end, y - 16, end, y + 16, demo.MUTED, width=3)
    ticks = y + 110
    for i in range(STEPS + 1):
        s = i / STEPS
        tx = x0 + (x1 - x0) * ease_in_sine(s)
        demo.dot(cv, tx, ticks, 7, color=demo.TEAL if s <= t else demo.MUTED, alpha=1.0 if s <= t else 0.35)
    x = x0 + (x1 - x0) * ease_in_sine(t)
    demo.dot(cv, x, y, 40)
    cv.mark('dot', x - 40, y - 40, 80, 80)


TECHNIQUE = Technique(
    id='ease-in-sine',
    name='Ease In Sine',
    family='principles',
    group='Easing',
    aliases=('sine in', 'easeInSine'),
    definition='A move that sets off softly from rest and picks up speed smoothly, '
               'following the gentle rise of a sine curve until it reaches full pace at the end.',
    phrasings=('starts slow and gently speeds up',
               'eases out of its starting spot without a jolt',
               'a soft, subtle acceleration from standstill'),
    related=('slow-in-and-slow-out', 'smooth-scroll-inertia', 'sine-wave-text', 'sine-wave-distortion',
             'settle', 'oscillation'),
    api=('videobuilder.techniques.principles.ease_in_sine.ease_in_sine',),
    demo=lambda: demo.film(draw),
)

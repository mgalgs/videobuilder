"""Ease Out Cubic: the everyday deceleration curve -- quick off the mark, then
slowing steadily until it stops dead on the target, with no overshoot."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_out_cubic(x):
    """Progress `x` in [0, 1] -> eased progress: 1 - (1 - x)^3, fast at the
    start and flattening to a stop at 1."""
    return 1 - (1 - vb.clamp01(x)) ** 3


START, END = 0.4, 1.9  # seconds the move runs


def draw(n, cv):
    x0, x1, y = demo.W * 0.2, demo.W * 0.8, demo.H / 2 - 40
    track = demo.H / 2 + 90
    demo.floor(cv, track, color=demo.LINE)
    # One tick per frame of the move so far: wide gaps early, bunched up at the end.
    for k in range(round(START * demo.FPS), n + 1):
        p = ease_out_cubic(demo.phase(k, START, END))
        tx = x0 + (x1 - x0) * p
        cv.line(tx, track - 18, tx, track + 18, demo.TEAL, width=3)
        if p >= 1:
            break
    cx = x0 + (x1 - x0) * ease_out_cubic(demo.phase(n, START, END))
    demo.card(cv, cx, y)


CAPABILITY = Capability(
    id='ease-out-cubic',
    name='Ease Out Cubic',
    family='principles',
    group='Easing',
    aliases=('easeOutCubic', 'cubic out', 'power3 out', 'decelerate'),
    definition='A move that leaves quickly and then slows down steadily, coming to a soft stop exactly '
               'on its target without overshooting.',
    phrasings=('slides in fast and gently slows to a stop',
               'glides into place and settles',
               'decelerates smoothly as it arrives'),
    related=('slow-in-and-slow-out', 'smooth-scroll-inertia', 'interruptible-motion', 'roll-up',
             'zoom-out-reveal', 'dolly-in-and-out'),
    api=('videobuilder.capabilities.principles.ease_out_cubic.ease_out_cubic',),
    demo=lambda: demo.film(draw),
)

"""Ease Out Quart: a decelerating curve, 1 - (1 - x)^4 -- it leaves at full
speed and spends most of its time gently closing the last bit of distance."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START, END = 0.5, 1.9
TICKS = 12  # evenly spaced moments of the move, left behind as ghosts


def ease_out_quart(x):
    """Progress `x` in [0, 1] -> eased progress: fast at the start, slowing
    hard into 1 with no overshoot (the quartic ease-out)."""
    return 1 - (1 - vb.clamp01(x)) ** 4


def draw(n, cv):
    x0, x1, y = 300, demo.W - 300, demo.H / 2
    at = lambda p: x0 + (x1 - x0) * ease_out_quart(p)  # noqa: E731
    p = demo.phase(n, START, END)
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it comes to rest
    # Ghosts at equal time steps: wide gaps early, bunched up near the end.
    for k in range(TICKS + 1):
        q = k / TICKS
        if q > p:
            break
        cv.rect(at(q) - 3, y + 120, 6, 26, demo.MUTED, radius=3, alpha=0.8)
        demo.card(cv, at(q), y, color=demo.MUTED, alpha=0.12)
    demo.card(cv, at(p), y)


CAPABILITY = Capability(
    id='ease-out-quart',
    name='Ease Out Quart',
    family='principles',
    group='Easing',
    aliases=('quartic ease-out', 'ease out quartic', 'easeOutQuart'),
    definition='A move that sets off at full speed and then slows down steeply, gliding the last stretch '
               'into place without overshooting.',
    phrasings=('starts quick and slows down smoothly as it arrives',
               'zips in and gently settles at the end',
               'a strong deceleration into the final position'),
    related=('slow-in-and-slow-out', 'asymmetric-fast-in-slow-out', 'settle', 'liquify',
             'smooth-scroll-inertia', 'dolly-in-and-out'),
    api=('videobuilder.capabilities.principles.ease_out_quart.ease_out_quart',),
    demo=lambda: demo.film(draw),
)

"""Elastic Ease Out: an easing curve that shoots past its target and wobbles
back and forth across it, each swing smaller, before it comes to rest."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def elastic_ease_out(x, period=0.3):
    """Progress `x` in [0, 1] -> eased progress that overshoots 1 and
    oscillates around it with an exponentially shrinking swing. `period` is
    the length of one swing as a fraction of the move; smaller wobbles more
    (0.3 is the classic curve)."""
    x = vb.clamp01(x)
    if x in (0.0, 1.0):
        return x
    return 2 ** (-10 * x) * math.sin((x - period / 4) * 2 * math.pi / period) + 1


def draw(n, cv):
    r, y = 28, demo.H / 2
    x0, x1 = demo.W * 0.18, demo.W * 0.6
    track = y + r + 18
    cv.line(80, track, demo.W - 80, track, demo.LINE, width=2)
    cv.line(x1, track - 12, x1, track + 12, demo.TEAL, width=3)  # where it comes to rest
    x = x0 + (x1 - x0) * elastic_ease_out(demo.phase(n, 0.4, 2.4))
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='elastic-ease-out',
    name='Elastic Ease Out',
    family='principles',
    group='Easing',
    aliases=('easeOutElastic', 'elastic out', 'rubber ease out', 'ease out elastic'),
    definition='A move that shoots past its target and swings back and forth across it, '
               'each swing smaller than the last, until it settles like a plucked elastic.',
    phrasings=('overshoots and wobbles back and forth before it stops',
               'snaps into place with a springy jiggle',
               'settles with a rubbery wobble at the end'),
    related=('rubber-band-overscroll', 'elastic-stretch', 'rubber-band-snap', 'slow-in-and-slow-out',
             'squash-and-stretch', 'overshoot-bounce-in'),
    api=('videobuilder.capabilities.principles.elastic_ease_out.elastic_ease_out',),
    demo=lambda: demo.film(draw),
)

"""Steps Easing: an easing curve that holds still and then jumps, so progress
moves in a fixed number of equal hops instead of gliding (CSS `steps()`)."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def steps(count, position='end'):
    """An easing curve `x -> y` over [0, 1] that climbs in `count` equal jumps.
    `position='end'` holds each value for its whole step and jumps at the
    step's end (0 at the start, 1 only at x = 1); `'start'` jumps at the
    step's start (already 1/count just after 0). Works as `ease=` anywhere a
    curve is taken, e.g. `vb.interpolate(t, xs, ys, ease=steps(8))`."""
    if not isinstance(count, int) or count < 1:
        raise ValueError(f'steps: count must be a positive int, not {count!r}')
    if position not in ('start', 'end'):
        raise ValueError(f"steps: position must be 'start' or 'end', not {position!r}")
    rnd = math.ceil if position == 'start' else math.floor

    def ease(x):
        x = vb.clamp01(x)
        return min(rnd(x * count), count) / count
    return ease


COUNT = 8


def draw(n, cv):
    r, y = 30, demo.H / 2 - 20
    x0, x1 = 120, demo.W - 120
    p = steps(COUNT)(demo.phase(n, 0.4, 2.6))
    k = round(p * COUNT)  # which stop the dot is on
    ty = y + r + 40
    cv.line(x0, ty, x1, ty, demo.LINE, width=3)
    for i in range(COUNT + 1):
        x = x0 + (x1 - x0) * i / COUNT
        on = i <= k
        cv.line(x, ty - 14, x, ty + 14, demo.TEAL if on else demo.MUTED, width=3, alpha=1 if on else 0.6)
        if i < k:  # the stops it has already jumped through
            cv.arc(x, y, r, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.5)
    x = x0 + (x1 - x0) * p
    demo.dot(cv, x, y, r)
    cv.mark('dot', x - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='steps-easing',
    name='Steps Easing',
    family='principles',
    group='Easing',
    aliases=('steps()', 'step-start', 'step-end', 'discrete easing', 'stepped easing'),
    definition='A move that freezes and then snaps forward in a handful of equal jumps, '
               'ticking toward its target like a clock hand instead of gliding.',
    phrasings=('moves in choppy little jumps instead of sliding smoothly',
               'ticks across in steps like a clock',
               'make it snap from position to position, no smooth motion'),
    related=('speed-ramp', 'step-by-step-process-reveal', 'asymmetric-fast-in-slow-out', 'hop-cycle',
             'friction-deceleration', 'eased-stagger'),
    api=('videobuilder.capabilities.principles.steps_easing.steps',),
    demo=lambda: demo.film(draw),
)

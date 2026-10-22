"""Critically Damped Spring: videobuilder already has it as a spring at damping
ratio 1 (`vb.critical` params into `vb.spring_at`), so this entry only names
it and demos it, with the curve traced under the card to show it never passes
its target."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START = 0.4                  # seconds: when the spring is released
SPRING = vb.critical(40.0)  # damping ratio exactly 1; settles in about a second


def draw(n, cv):
    p = vb.spring_at(n - START * demo.FPS, demo.FPS, **SPRING)
    x0, x1, y = demo.W * 0.2, demo.W * 0.75, demo.H * 0.3
    cv.outline(x1 - 90, y - 55, 180, 110, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it comes to rest
    demo.card(cv, x0 + (x1 - x0) * p, y, w=180, h=110)

    # The response so far, time across and position up: it rises and flattens onto the target line.
    gx0, gx1, gy0, gy1 = demo.W * 0.12, demo.W * 0.88, demo.H * 0.88, demo.H * 0.6
    cv.line(gx0, gy0, gx1, gy0, demo.LINE, width=2)
    cv.line(gx0, gy1, gx1, gy1, demo.MUTED, width=2, alpha=0.5)
    total = round(demo.SECONDS * demo.FPS) - 1
    prev = None
    for k in range(n + 1):
        q = vb.spring_at(k - START * demo.FPS, demo.FPS, **SPRING)
        pt = (gx0 + (gx1 - gx0) * k / total, gy0 + (gy1 - gy0) * q)
        if prev:
            cv.line(*prev, *pt, demo.ACCENT, width=3)
        prev = pt
    demo.dot(cv, *prev, r=6)


CAPABILITY = Capability(
    id='critically-damped-spring',
    name='Critically Damped Spring',
    family='principles',
    group='Physics',
    aliases=('critical damping', 'no-bounce spring', 'damping ratio 1'),
    definition='A spring-driven move that gets to its target as quickly as it can and settles there '
               'without ever going past it or wobbling.',
    phrasings=('springs into place fast but with no bounce at all',
               'a firm, physical landing that stops dead on the mark',
               'use a spring, but tune it so it never overshoots'),
    related=('overshoot-bounce-in', 'spring-return', 'springs-network', 'mass-spring-cloth',
             'interruptible-motion', 'spring-drag-letters'),
    api=('videobuilder.critical', 'videobuilder.spring_at'),
    demo=lambda: demo.film(draw),
)

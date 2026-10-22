"""Linear Easing: videobuilder already has it as `vb.linear`, so this entry
only names it and demos it -- a dot crossing at one steady speed, leaving a
mark every equal slice of time, so the marks come out evenly spaced."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

STEPS = 12  # equal slices of time; with no easing they make equal slices of distance


def draw(n, cv):
    start, end = 0.3, 2.7
    p = vb.linear(demo.phase(n, start, end))
    x0, x1, y = 140, demo.W - 140, 140
    cv.line(x0, y, x1, y, demo.LINE, width=2)
    for x in (x0, x1):
        cv.line(x, y - 12, x, y + 12, demo.MUTED, width=2)
    for k in range(STEPS + 1):  # one tick per slice of time, lit once the dot has passed it
        q = k / STEPS
        lit = q <= p + 1e-9
        demo.dot(cv, x0 + (x1 - x0) * vb.linear(q), y + 56, 6 if lit else 3,
                 color=demo.TEAL if lit else demo.MUTED, alpha=1.0 if lit else 0.5)
    x = x0 + (x1 - x0) * p
    demo.dot(cv, x, y, 30)
    cv.mark('dot', x - 30, y - 30, 60, 60)

    # position over time: a straight line, the same slope all the way
    gx, gy, gw, gh = demo.W / 2 - 160, 260, 320, 180
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.MUTED, width=2)
    cv.line(gx, gy, gx, gy + gh, demo.MUTED, width=2)
    cv.line(gx, gy + gh, gx + gw * p, gy + gh - gh * p, demo.ACCENT, width=3)
    demo.dot(cv, gx + gw * p, gy + gh - gh * p, 6)
    demo.word(cv, 'time', gx + gw / 2, gy + gh + 22, size=18, color=demo.MUTED, weight=600)


CAPABILITY = Capability(
    id='linear-easing',
    name='Linear Easing',
    family='principles',
    group='Easing',
    aliases=('linear', 'constant speed', 'ease none', 'no easing'),
    definition='A move that keeps exactly the same speed from the first frame to the last, '
               'with no speeding up at the start and no slowing down at the end.',
    phrasings=('moves across at a steady, even pace',
               'slides at constant speed without easing',
               'glides like a conveyor belt, same speed the whole way'),
    related=('asymmetric-fast-in-slow-out', 'friction-deceleration', 'slow-in-and-slow-out', 'eased-stagger',
             'inertia', 'smooth-scroll-inertia'),
    api=('videobuilder.linear',),
    demo=lambda: demo.film(draw),
)

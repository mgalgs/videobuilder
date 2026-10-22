"""Ease In-Out Quint: the fifth-power S-curve, which creeps off the start,
covers almost all the distance in a short rush through the middle, and
creeps into the end."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_out_quint(x):
    """Progress `x` in [0, 1] -> eased progress: 16x^5 for the first half,
    mirrored for the second, so both ends are flat and the middle is steep."""
    x = vb.clamp01(x)
    if x < 0.5:
        return 16 * x ** 5
    return 1 - (-2 * x + 2) ** 5 / 2


START, END = 0.4, 2.6
GX, GY, GW, GH = demo.W / 2 - 160, demo.H - 60, 320, 170   # the graph: bottom-left corner and size


def _curve(cv, upto, color, width, alpha=1.0, steps=60):
    pts = [(GX + GW * i / steps * upto, GY - GH * ease_in_out_quint(i / steps * upto)) for i in range(steps + 1)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, color, width=width, alpha=alpha)


def draw(n, cv):
    t = demo.phase(n, START, END)
    p = ease_in_out_quint(t)
    x0, x1, y = 170, demo.W - 170, 130
    cv.line(x0, y + 105, x1, y + 105, demo.MUTED, width=2, alpha=0.5)   # the track
    cv.line(x0, y + 105, x0 + (x1 - x0) * p, y + 105, demo.TEAL, width=4)
    demo.card(cv, x0 + (x1 - x0) * p, y)
    cv.line(GX, GY, GX + GW, GY, demo.MUTED, width=2, alpha=0.6)      # graph axes
    cv.line(GX, GY, GX, GY - GH, demo.MUTED, width=2, alpha=0.6)
    _curve(cv, 1.0, demo.MUTED, 2, alpha=0.4)                          # the whole curve, faint
    if t > 0:
        _curve(cv, t, demo.TEAL, 3)                                    # the part travelled so far
    demo.dot(cv, GX + GW * t, GY - GH * p, 7, color=demo.INK)


CAPABILITY = Capability(
    id='ease-in-out-quint',
    name='Ease In-Out Quint',
    family='principles',
    group='Easing',
    aliases=('easeInOutQuint', 'quintic ease in-out', 'power 5 in-out', 'dramatic ease in-out'),
    definition='A move that barely stirs at first, sweeps almost the whole way in a quick burst '
               'through the middle, then crawls to a stop, following a fifth-power curve.',
    phrasings=('a really dramatic slow start and slow finish with a fast middle',
               'glides off slowly, whooshes across, and settles gently like a camera move',
               'a strong S-curve ease on both ends'),
    related=('slow-in-and-slow-out', 'dolly-in-and-out', 'smooth-scroll-inertia', 'pulldown-judder',
             'push-in', 'punch-in'),
    api=('videobuilder.capabilities.principles.ease_in_out_quint.ease_in_out_quint',),
    demo=lambda: demo.film(draw),
)

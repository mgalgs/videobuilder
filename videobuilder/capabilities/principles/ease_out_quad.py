"""Ease Out Quad: the gentlest standard deceleration -- a move that leaves at
full speed and slows steadily (a parabola) until it stops on its target."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_out_quad(x):
    """Progress `x` in [0, 1] -> eased progress: starts at twice linear speed
    and slows evenly to rest, `1 - (1 - x)^2`."""
    x = vb.clamp01(x)
    return 1 - (1 - x) * (1 - x)


START, END = 0.5, 2.1
TICKS = 9  # ghost cards at equal steps in time: their spacing shrinks as the move slows


def draw(n, cv):
    w, h = 150, 96
    x0, x1, y = demo.W / 2 - 330, demo.W / 2 + 330, demo.H / 2
    at = lambda p: x0 + (x1 - x0) * ease_out_quad(p)  # noqa: E731
    demo.floor(cv, y + 100, color=demo.LINE)
    p = demo.phase(n, START, END)
    for i in range(TICKS):
        q = i / (TICKS - 1)
        if q > p:
            break
        x = at(q)
        cv.line(x, y + 88, x, y + 112, demo.MUTED, width=3)
        cv.outline(x - w / 2, y - h / 2, w, h, demo.MUTED, width=2, radius=14, alpha=0.35)
    demo.card(cv, at(p), y, w=w, h=h)


TECHNIQUE = Technique(
    id='ease-out-quad',
    name='Ease Out Quad',
    family='principles',
    group='Easing',
    aliases=('quadratic ease out', 'ease out quadratic', 'decelerate', 'easeOutQuad'),
    definition='A move that sets off at its quickest and slows down at an even rate, '
               'gently coasting to a stop on its target.',
    phrasings=('slides in and gently slows to a stop',
               'starts quick and decelerates softly into place',
               'a soft, natural slow-down at the end of the move'),
    related=('slow-in-and-slow-out', 'asymmetric-fast-in-slow-out', 'settle', 'inertia',
             'dolly-in-and-out', 'friction-deceleration'),
    api=('videobuilder.techniques.principles.ease_out_quad.ease_out_quad',),
    demo=lambda: demo.film(draw),
)

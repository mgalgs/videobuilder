"""Ease In Quad: the gentlest of the standard accelerating curves, progress
squared, so a move starts from rest and picks up speed all the way to its end."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_quad(x):
    """Progress `x` in [0, 1] -> eased progress `x * x`: zero speed at the
    start, twice the average speed at the end."""
    x = vb.clamp01(x)
    return x * x


START, END = 0.5, 2.1  # seconds the move runs for in the demo


def draw(n, cv):
    x0, x1, y = 260, demo.W - 260, demo.H / 2
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it ends up
    # Where the card was at even steps of time: the gaps widen as it speeds up.
    steps = 10
    for i in range(steps + 1):
        t = START + (END - START) * i / steps
        if t * demo.FPS > n:
            break
        tx = x0 + (x1 - x0) * ease_in_quad(i / steps)
        demo.dot(cv, tx, y + 130, 9, color=demo.TEAL, alpha=0.85)
    demo.card(cv, x0 + (x1 - x0) * ease_in_quad(demo.phase(n, START, END)), y)


CAPABILITY = Capability(
    id='ease-in-quad',
    name='Ease In Quad',
    family='principles',
    group='Easing',
    aliases=('quadratic ease in', 'ease in quadratic', 'easeInQuad', 'accelerate'),
    definition='A move that begins at a standstill and speeds up steadily, '
               'reaching its fastest at the very moment it stops.',
    phrasings=('starts slow and gathers speed as it goes',
               'gently accelerates out of frame',
               'eases out of rest and picks up pace toward the end'),
    related=('asymmetric-fast-in-slow-out', 'slow-in-and-slow-out', 'settle', 'smooth-scroll-inertia',
             'inertia', 'friction-deceleration'),
    api=('videobuilder.capabilities.principles.ease_in_quad.ease_in_quad',),
    demo=lambda: demo.film(draw),
)

"""Ease In-Out Quad: the gentlest symmetric ease -- a move that gathers speed
along a parabola, peaks at the halfway point, then sheds it the same way."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_out_quad(x):
    """Progress `x` in [0, 1] -> eased progress: 2x^2 up to the midpoint, then
    the mirror of it, so speed rises linearly to a peak at 0.5 and falls back."""
    x = vb.clamp01(x)
    if x < 0.5:
        return 2 * x * x
    return 1 - 2 * (1 - x) * (1 - x)


START, END = 0.5, 2.5   # seconds the move runs between


def draw(n, cv):
    x0, x1, y = 260, demo.W - 260, demo.H / 2 - 40
    track = y + 150
    cv.outline(x0 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.4)  # where it starts
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.4)  # where it comes to rest
    cv.line(x0, track, x1, track, demo.LINE, width=2)
    # a tick where the card stood every few frames: bunched at both ends, spread out in the middle
    for k in range(0, n + 1, 3):
        p = ease_in_out_quad(demo.phase(k, START, END))
        demo.dot(cv, x0 + (x1 - x0) * p, track, 7, color=demo.TEAL, alpha=0.8)
    p = ease_in_out_quad(demo.phase(n, START, END))
    demo.card(cv, x0 + (x1 - x0) * p, y)


CAPABILITY = Capability(
    id='ease-in-out-quad',
    name='Ease In-Out Quad',
    family='principles',
    group='Easing',
    aliases=('quadratic ease in-out', 'ease in out quad', 'easeInOutQuad', 'soft ease in-out'),
    definition='A move that picks up speed gently from rest, is quickest at its midpoint, and slows '
               'just as gently into its stop, with the speed changing at a steady rate both ways.',
    phrasings=('glides across with a soft start and a soft stop',
               'speeds up then slows down evenly, nothing too punchy',
               'a gentle, balanced acceleration and deceleration'),
    related=('slow-in-and-slow-out', 'asymmetric-fast-in-slow-out', 'smooth-scroll-inertia', 'inertia',
             'settle', 'dolly-in-and-out'),
    api=('videobuilder.capabilities.principles.ease_in_out_quad.ease_in_out_quad',),
    demo=lambda: demo.film(draw),
)

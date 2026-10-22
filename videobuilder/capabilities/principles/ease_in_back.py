"""Ease In Back: an easing curve that first pulls a little the wrong way, as
if winding up, then accelerates hard toward its target -- the mirror of
`ease_out_back`, with the overshoot at the start instead of the end."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_back(x, overshoot=1.70158):
    """Progress `x` in [0, 1] -> eased progress that dips below 0 before
    rising to 1. `overshoot` sets how far back it pulls (the default dips
    about 10%; 0 is a plain cubic ease-in)."""
    x = vb.clamp01(x)
    return (overshoot + 1) * x ** 3 - overshoot * x ** 2


def draw(n, cv):
    p = ease_in_back(demo.phase(n, 0.6, 1.8))
    x0, x1, y = demo.W / 2 - 280, demo.W / 2 + 280, demo.H / 2
    cv.outline(x0 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.35)  # where it starts
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it lands
    demo.card(cv, x0 + (x1 - x0) * p, y)


CAPABILITY = Capability(
    id='ease-in-back',
    name='Ease In Back',
    family='principles',
    group='Easing',
    aliases=('back in', 'ease in back', 'anticipation ease', 'wind-up ease'),
    definition='A move that first backs off a little in the opposite direction, then speeds up '
               'toward its target and arrives at full speed.',
    phrasings=('pulls back slightly before shooting off',
               'winds up and then launches across',
               'leans back a touch before it takes off'),
    related=('slow-in-and-slow-out', 'anticipation', 'smooth-scroll-inertia', 'reverse-playback',
             'settle', 'follow-through'),
    api=('videobuilder.capabilities.principles.ease_in_back.ease_in_back',),
    demo=lambda: demo.film(draw),
)

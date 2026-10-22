"""Ease Out Back: videobuilder already has it as `vb.ease_out_back`, so this
entry only names it and demos it -- the template for an existing API."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw(n, cv):
    p = vb.ease_out_back(demo.phase(n, 0.5, 1.6))
    x0, x1, y = demo.W / 2 - 380, demo.W / 2, demo.H / 2
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it comes to rest
    demo.card(cv, x0 + (x1 - x0) * p, y)


CAPABILITY = Capability(
    id='ease-out-back',
    name='Ease Out Back',
    family='principles',
    group='Easing',
    aliases=('back out', 'overshoot ease'),
    definition='A move that starts fast, runs a little past its target, then eases back to rest on it.',
    phrasings=('slides in and overshoots a touch before settling',
               'pops into place with a little bounce-back',
               'arrives with a small overshoot'),
    related=('bounce-ease-out', 'ease-in-back', 'spring-settle'),
    api=('videobuilder.ease_out_back',),
    demo=lambda: demo.film(draw),
)

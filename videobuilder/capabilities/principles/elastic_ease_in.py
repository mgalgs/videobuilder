"""Elastic Ease In: an easing curve that winds up like a plucked spring --
it quivers around the start in swings that keep growing, then lets go and
snaps all the way to the target."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def elastic_ease_in(x, period=0.3):
    """Progress `x` in [0, 1] -> eased progress: a sine oscillation about 0
    whose amplitude grows exponentially, ending exactly on 1. `period` is the
    swing length as a fraction of the move; smaller means more wiggles. The
    swings dip below 0, so the subject pulls back past its start."""
    x = vb.clamp01(x)
    if x <= 0 or x >= 1:
        return x
    t = x - 1
    return -(2 ** (10 * t)) * math.sin((t - period / 4) * 2 * math.pi / period)


def draw(n, cv):
    # The move starts before the first frame so its sub-pixel opening quivers stay off screen,
    # and a slightly short period gives five visible swings before the launch.
    p = elastic_ease_in(demo.phase(n, -0.5, 2.2), period=0.25)
    w, h = 200, 124
    # The curve pulls back ~0.44 of the travel, so the start sits far enough right
    # that the card's deepest back swing still clears the left edge.
    x0, x1, y = demo.W / 2 - 140, demo.W / 2 + 300, demo.H / 2
    cv.outline(x0 - w / 2, y - h / 2, w, h, demo.MUTED, width=2, radius=18, alpha=0.3)  # where it starts
    cv.outline(x1 - w / 2, y - h / 2, w, h, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it comes to rest
    demo.card(cv, x0 + (x1 - x0) * p, y, w=w, h=h)


CAPABILITY = Capability(
    id='elastic-ease-in',
    name='Elastic Ease In',
    family='principles',
    group='Easing',
    aliases=('ease in elastic', 'elastic in'),
    definition='A move that first jiggles back and forth around its starting point in ever wider swings, '
               'then breaks loose and shoots to its target.',
    phrasings=('wobbles in place like a spring winding up, then flies off',
               'shakes more and more before it launches',
               'a springy wind-up before the move'),
    related=('elastic-stretch', 'rubber-band-snap', 'rubber-band-overscroll', 'slow-in-and-slow-out',
             'asymmetric-fast-in-slow-out', 'wobble'),
    api=('videobuilder.capabilities.principles.elastic_ease_in.elastic_ease_in',),
    demo=lambda: demo.film(draw),
)

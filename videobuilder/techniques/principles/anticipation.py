"""Anticipation: before the real move, a short pull the opposite way -- a
wind-up -- so the eye is ready for where the thing is about to go."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def anticipate(x, pull=0.15, windup=0.35):
    """Progress `x` in [0, 1] -> eased progress that first eases back to
    `-pull` over the first `windup` share of the time, then releases fast and
    decelerates onto 1. Use it in place of any ease: `a + (b - a) * anticipate(p)`."""
    x = vb.clamp01(x)
    if x < windup:
        return -pull * (1 - math.cos(math.pi * x / windup)) / 2
    return -pull + (1 + pull) * vb.ease_out_quint((x - windup) / (1 - windup))


def windup_depth(x, windup=0.35):
    """How far into the wind-up `x` is, 0 -> 1 -> 0: peaks at the end of the
    pull-back and lets go quickly after release. Handy for a squash while it
    gathers itself."""
    x = vb.clamp01(x)
    if x < windup:
        return (1 - math.cos(math.pi * x / windup)) / 2
    return max(0.0, 1 - (x - windup) / 0.12)


START, LENGTH = 0.5, 1.8


def draw(n, cv):
    r, ground = 28, demo.H - 150
    x0, x1 = 220, demo.W - 220
    p = demo.phase(n, START, START + LENGTH)
    x = x0 + (x1 - x0) * anticipate(p)
    demo.floor(cv, ground)
    cv.line(x1, ground - 12, x1, ground + 12, demo.MUTED, width=3)  # where it is headed
    demo.dot(cv, x0, ground - r, r, color=demo.MUTED, alpha=0.25)  # where it started
    d = windup_depth(p)
    v = (anticipate(min(1, p + 0.01)) - anticipate(p)) / 0.01 if 0 < p < 1 else 0
    stretch = min(0.35, max(0.0, v) * 0.05)
    sx, sy = 1 - 0.18 * d + stretch, 1 + 0.12 * d - stretch * 0.5  # crouch back, then stretch on release
    cv.ctx.save()
    cv.ctx.translate(x, ground)
    cv.ctx.scale(sx, sy)
    demo.dot(cv, 0, -r, r)
    cv.ctx.restore()
    cv.mark('ball', x - r * sx, ground - 2 * r * sy, 2 * r * sx, 2 * r * sy)


TECHNIQUE = Technique(
    id='anticipation',
    name='Anticipation',
    family='principles',
    group='Disney principles',
    aliases=('wind-up', 'windup', 'pre-action'),
    definition='Just before a big move, the object eases a little the opposite way, as if gathering itself, '
               'then springs off fast in the real direction.',
    phrasings=('pulls back a bit before it shoots forward',
               'give it a little wind-up before it moves',
               'crouches backward first, then launches toward the target'),
    related=('ease-in-back', 'delay', 'reverse-playback', 'interruptible-motion', 'staggered-cascade-reveal',
             'uncover'),
    api=('videobuilder.techniques.principles.anticipation.anticipate',
         'videobuilder.techniques.principles.anticipation.windup_depth'),
    demo=lambda: demo.film(draw),
)

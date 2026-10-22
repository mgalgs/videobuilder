"""Jiggle: a brief, fast shiver about an object's resting place, its swing
dying away within a fraction of a second -- a nudge rather than a move."""
import math

from .. import _demo as demo
from ..schema import Capability


def jiggle(t, amount=1.0, hz=9.0, decay=6.0):
    """Offset at `t` seconds since the jiggle started: a sine at `hz` cycles
    per second whose swing starts at `amount` and shrinks by `e` every
    `1 / decay` seconds. 0 before it starts, so it always rests at 0. Scale it
    to pixels, degrees or a scale factor; sum calls for repeated nudges."""
    if t <= 0:
        return 0.0
    return amount * math.exp(-decay * t) * math.sin(2 * math.pi * hz * t)


NUDGES = (0.5, 1.7)  # seconds the card is nudged


def draw(n, cv):
    t = n / demo.FPS
    dx = sum(jiggle(t - at, 34) for at in NUDGES)
    turn = sum(jiggle(t - at, 0.07, hz=9.0, decay=6.0) for at in NUDGES)
    cx, cy = demo.W / 2, demo.H / 2
    cv.outline(cx - 130, cy - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it rests
    for at in NUDGES:  # a quick tick under the card at each nudge
        k = demo.phase(n, at, at + 0.35)
        if 0 < k < 1:
            cv.line(cx - 60 - 40 * k, cy + 120, cx + 60 + 40 * k, cy + 120, demo.TEAL, width=4, alpha=1 - k)
    cv.ctx.save()
    cv.ctx.translate(cx + dx, cy)
    cv.ctx.rotate(turn)
    demo.card(cv, 0, 0)
    cv.ctx.restore()


CAPABILITY = Capability(
    id='jiggle',
    name='Jiggle',
    family='principles',
    group='Physics',
    aliases=('jitter spring', 'quick tremble', 'shiver'),
    definition='An object shivers rapidly back and forth around where it sits, the shake fading out '
               'within a fraction of a second.',
    phrasings=('give the card a quick little shiver when it is tapped',
               'make it tremble for a moment and then go still',
               'a fast wobble that dies away right away'),
    related=('wiggle-path', 'handheld-shake', 'jitter-and-boil-text', 'tape-wobble', 'scanline-jitter',
             'icon-hover-bounce'),
    api=('videobuilder.capabilities.principles.jiggle.jiggle',),
    demo=lambda: demo.film(draw),
)

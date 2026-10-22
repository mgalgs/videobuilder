"""Idle Float Bob: a resting element drifts up and down on a slow sine wave,
over and over, so it reads as hovering in place rather than sitting still."""
import math

from .. import _demo as demo
from ..schema import Capability


def bob(t, amplitude=14.0, period=2.0, phase=0.0):
    """The vertical offset at time `t` seconds of something bobbing `amplitude`
    px either side of its rest point, one full up-and-down every `period`
    seconds. Negative is up (screen y grows downward); it starts at rest and
    rises first. `phase` (0 -> 1, a fraction of a cycle) staggers several
    floating things so they don't move in lockstep. A whole number of periods
    loops seamlessly."""
    return -amplitude * math.sin(2 * math.pi * (t / period + phase))


def draw(n, cv):
    cx, rest, amp = demo.W / 2, demo.H / 2 - 30, 36
    dy = bob(n / demo.FPS, amplitude=amp, period=1.5)
    lift = (-dy + amp) / (2 * amp)  # 0 at the bottom of the swing, 1 at the top
    ground = rest + 170
    cv.ctx.save()  # the shadow below shrinks and fades as the card floats up, sells the hover
    cv.ctx.translate(cx, ground)
    cv.ctx.scale(1, 0.16)
    demo.dot(cv, 0, 0, 120 - 30 * lift, color='#000000', alpha=0.4 - 0.2 * lift)
    cv.ctx.restore()
    demo.card(cv, cx, rest + dy)


CAPABILITY = Capability(
    id='idle-float-bob',
    name='Idle Float Bob',
    family='principles',
    group='Cycles & loops',
    aliases=('hover bob', 'floating loop', 'bobbing idle'),
    definition='A resting element drifts smoothly up and down in an endless slow wave, '
               'as if it were hovering or floating on water.',
    phrasings=('make it float gently up and down while it waits',
               'give the icon a soft hovering bob',
               'have the card bob in place like it is floating'),
    related=('floating-label', 'empty-state-idle-loop', 'floating-reaction-emoji',
             'hover-letter-displacement', 'bouncing-dots', 'smooth-scroll-inertia'),
    api=('videobuilder.capabilities.principles.idle_float_bob.bob',),
    demo=lambda: demo.film(draw),
)

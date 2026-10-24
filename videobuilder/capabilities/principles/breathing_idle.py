"""Breathing Idle: something at rest slowly swells and settles on a steady
rhythm, so a still screen keeps a pulse of life without asking for attention."""
import math

from .. import _demo as demo
from ..schema import Capability


def breathing_idle(t, period=2.0, depth=0.04, start=0.0):
    """The scale at time `t` (seconds) of a slow breath: 1 at rest, swelling
    to `1 + depth` and back once every `period` seconds from `start`. It
    leaves rest with no velocity, so it can begin on any held frame; a whole
    number of periods across a loop keeps the seam clean. Before `start` it
    holds at 1. (A cut-out character's breath is `vb.Puppet.breath`.)"""
    if t <= start:
        return 1.0
    return 1 + depth * (1 - math.cos(2 * math.pi * (t - start) / period)) / 2


def draw(n, cv):
    t, depth = n / demo.FPS, 0.08
    s = breathing_idle(t, period=1.5, depth=depth)
    b = (s - 1) / depth                       # 0 at rest, 1 at the top of the breath
    cx, cy, r = demo.W / 2, demo.H / 2, 120
    for k, a in ((1.55, 0.06), (1.3, 0.1)):   # a soft halo that swells with it
        demo.dot(cv, cx, cy, r * s * (k + 0.12 * b), color=demo.ACCENT, alpha=a * (0.5 + 0.5 * b))
    demo.dot(cv, cx, cy, r * s)
    demo.word(cv, 'Start', cx, cy, size=int(56 * s))
    cv.mark('button', cx - r * s, cy - r * s, 2 * r * s, 2 * r * s)


CAPABILITY = Capability(
    id='breathing-idle',
    name='Breathing Idle',
    family='principles',
    group='Cycles & loops',
    aliases=('breathing animation', 'idle breathing', 'idle pulse', 'breathe', 'heartbeat text'),
    definition='An element waiting on screen gently grows and shrinks back in a slow, even rhythm, '
               'as if quietly breathing while nothing else happens.',
    phrasings=('make the button softly breathe while it waits',
               'give the idle logo a slow in-and-out pulse so it feels alive',
               'a gentle swelling loop on something that is just sitting there'),
    related=('empty-state-idle-loop', 'moving-hold', 'interruptible-motion', 'focus-breathing', 'scale-pulse',
             'delay'),
    api=('videobuilder.capabilities.principles.breathing_idle.breathing_idle', 'videobuilder.Puppet.breath'),
    demo=lambda: demo.film(draw),
)

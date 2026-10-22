"""Spin: the outgoing scene whirls around the frame's centre and shrinks
away, and the incoming scene keeps the same spin going as it grows back to
fill the frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def spin(cv, a, b, p, turns=1.0, depth=0.2, color=demo.BG):
    """Draw the spin at progress `p` (0 -> 1): the frame turns `turns` full
    revolutions in all (clockwise; negative for anticlockwise), easing in and
    out, while it shrinks to `depth` of its size at the midpoint and grows
    back. `a(cv)` is the scene for the first half, `b(cv)` for the second;
    `color` fills the frame behind the turning picture.

    In a film, call it while two shots are live in an overlap, e.g.
    `spin(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = vb.clamp01(p)
    angle = 2 * math.pi * turns * vb.ease_in_out_quart(p)
    scale = 1 - (1 - depth) * math.sin(math.pi * p)
    cv.fill(color)
    c = cv.ctx
    c.save()
    c.translate(cv.width / 2, cv.height / 2)
    c.rotate(angle)
    c.scale(scale, scale)
    c.translate(-cv.width / 2, -cv.height / 2)
    with cv.clip(0, 0, cv.width, cv.height):
        (a if p < 0.5 else b)(cv)
    c.restore()


CAPABILITY = Capability(
    id='spin',
    name='Spin',
    family='transitions',
    group='Rotation and 3D',
    aliases=('spin transition', 'rotate transition', 'spin out, spin in'),
    definition='The whole picture whirls around its centre and shrinks away, and the next scene '
               'carries on the same turn as it grows back to fill the screen.',
    phrasings=('spin the first shot away and spin the next one in',
               'make the screen twirl round into the next scene',
               'rotate out of this clip and into the next'),
    related=('swirl', 'turntable-rotation', 'roll-up', 'globe-spin', 'gradient-border-spin', 'spin-blur'),
    api=('videobuilder.capabilities.transitions.spin.spin',),
    demo=lambda: demo.two_scenes(spin),
)

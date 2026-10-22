"""Secondary Action: a small gesture played on top of the main action without
interrupting it -- a figure keeps walking while one arm waves hello."""
import math
from dataclasses import replace

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

FRONT_ARM = ('front_arm', 'front_elbow')


def secondary_action(primary, gesture, amount, joints=FRONT_ARM):
    """`primary` (a `vb.stick.Pose`, e.g. a walk cycle's pose this frame)
    with only `joints` blended `amount` (0 -> 1) of the way to `gesture`'s
    angles; every other joint keeps the primary action untouched, so the
    walk, run or push carries on underneath the gesture."""
    return replace(primary, **{k: getattr(primary, k) + (getattr(gesture, k) - getattr(primary, k)) * amount
                               for k in joints})


def envelope(n, start, length, ramp=8):
    """How much of a secondary action shows at frame `n`: 0 before `start`,
    easing in over `ramp` frames, holding, then easing out to 0 by
    `start + length`. Feed it to `secondary_action` as `amount`."""
    up = vb.clamp01((n - start) / ramp)
    down = vb.clamp01((start + length - n) / ramp)
    return vb.ease_in_out_quart(min(up, down))


FIG = vb.Stick(height=250, ink=demo.INK, fill=demo.ACCENT, fps=demo.FPS)
GAIT = dict(period=0.75, stride=1.5)


def draw(n, cv):
    ground = demo.H - 80
    demo.floor(cv, ground)
    travel = FIG.speed('walk', **GAIT) * (demo.SECONDS * demo.FPS - 1)
    step = FIG.gait(n, 'walk', **GAIT)                                        # the primary action: a walk
    wave = envelope(n, 0.9 * demo.FPS, 1.3 * demo.FPS)                        # the secondary: a wave, mid-walk
    hello = vb.stick.Pose(front_arm=100, front_elbow=32 + 24 * math.sin(2 * math.pi * n / 12))   # hand up, waggling
    pose = secondary_action(step.pose, hello, wave)
    FIG.draw(cv, pose, (demo.W - travel) / 2 + step.x, ground - step.lift, face='happy', mark='figure')


TECHNIQUE = Technique(
    id='secondary-action',
    name='Secondary Action',
    family='principles',
    group='Disney principles',
    aliases=('secondary motion', 'supporting action'),
    definition='A smaller movement layered over the main one, such as a wave while walking, '
               'that adds personality without stopping or competing with the main movement.',
    phrasings=('have the character wave while it keeps walking',
               'add a little extra gesture on top of the main move',
               'something small happening alongside the main motion to give it life'),
    related=('cut-on-action', 'spring-motion', 'two-body-orbit', 'spin', 'multiples', 'recoil'),
    api=('videobuilder.techniques.principles.secondary_action.secondary_action',
         'videobuilder.techniques.principles.secondary_action.envelope',
         'videobuilder.Stick.gait'),
    demo=lambda: demo.film(draw),
)

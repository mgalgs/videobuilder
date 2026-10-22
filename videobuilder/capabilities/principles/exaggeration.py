"""Exaggeration: push a move past what's believable -- the crouch deeper, the
leap higher, the stretch longer, the squash flatter -- so the action reads
at a glance. `exaggerate` scales any pose value away from its rest;
`hop_pose` is a hop built on it, plain at `amount=1` and cartoonish above."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def exaggerate(value, rest=0.0, amount=2.0):
    """`value` pushed further from `rest`: its distance from rest times
    `amount` (1 leaves it alone, 2 doubles it, below 1 tones it down). Works on
    any pose number: an offset, an angle, a scale about 1."""
    return rest + (value - rest) * amount


def hop_pose(p, amount=1.0):
    """The pose of one hop at progress `p` in [0, 1]: `(lift, sx, sy)`, where
    `lift` is the height off the ground as a share of a plain hop's height and
    `sx`, `sy` scale the body about its feet. A crouch first, a stretch in the
    air, a squash and wobble on landing; `amount` exaggerates every one."""
    p = vb.clamp01(p)
    lift = squash = 0.0
    if p < 0.3:  # anticipation: sink down, then spring off
        c = p / 0.3
        squash = 0.08 * math.sin(math.pi * c ** 1.6)
    elif p < 0.75:  # airborne: stretched by speed, round at the top
        t = (p - 0.3) / 0.45
        lift = math.sin(math.pi * t)
        squash = -0.06 * abs(math.cos(math.pi * t))
    else:  # landing: a squash that springs back in a dying wobble
        t = (p - 0.75) / 0.25
        squash = 0.12 * math.exp(-3.5 * t) * math.cos(3 * math.pi * t)
    squash = exaggerate(squash, 0.0, amount)
    return exaggerate(lift, 0.0, amount ** 0.5), 1 + squash, max(0.2, 1 - squash)


def draw(n, cv):
    ground, r, rise = demo.H - 90, 36, 160
    p = demo.phase(n, 0.35, 2.55)
    demo.floor(cv, ground)
    lanes = ((demo.W * 0.3, 1.0, demo.MUTED, 'plain'), (demo.W * 0.7, 3.5, demo.ACCENT, 'exaggerated'))
    for cx, amount, color, label in lanes:
        lift, sx, sy = hop_pose(p, amount)
        cy = ground - lift * rise
        cv.ctx.save()
        cv.ctx.translate(cx, cy)
        cv.ctx.scale(sx, sy)
        demo.dot(cv, 0, -r, r, color=color)
        cv.ctx.restore()
        cv.mark(label, cx - r * sx, cy - 2 * r * sy, 2 * r * sx, 2 * r * sy)
        demo.word(cv, label, cx, ground + 36, size=24, color=demo.MUTED, weight=700)


CAPABILITY = Capability(
    id='exaggeration',
    name='Exaggeration',
    family='principles',
    group='Disney principles',
    aliases=('push the pose', 'cartoony motion', 'overacting'),
    definition='Every part of a move is pushed well past what is realistic, a deeper crouch, a bigger leap, '
               'a harder squash, so the action reads instantly and with more energy.',
    phrasings=('make the jump way more cartoony and over the top',
               'push the motion further so it really pops',
               'overdo the squash and stretch so it feels lively'),
    related=('slow-motion', 'push-in', 'moving-hold', 'focus-breathing', 'motion-blur', 'center-out-stagger'),
    api=('videobuilder.capabilities.principles.exaggeration.exaggerate',
         'videobuilder.capabilities.principles.exaggeration.hop_pose'),
    demo=lambda: demo.film(draw),
)

"""Impact: one thing strikes another, the striker's velocity changes in an
instant (it stops dead or rebounds), and the thing it hit is shoved, squashes
against the blow and wobbles back to rest."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def impact(t, shove=40.0, squash=0.2, hz=4.0, damping=0.3):
    """The receiver's reaction `t` seconds after it is hit -> (dx, sx, sy).

    `dx`: px it is pushed along the blow, jumping out at once and springing
    back to 0 past a small overshoot. `sx`, `sy`: its scale across and along
    the blow's line of travel, flattened against the blow by up to `squash`
    and bulging the other way to keep its area, wobbling out over the same
    spring. `hz` and `damping` set that spring (a damping ratio below 1).
    Before the hit (t < 0) it is (0, 1, 1). Scale about the face that was hit
    or the ground it stands on, so it looks pressed rather than shrunk."""
    if t < 0:
        return 0.0, 1.0, 1.0
    w0 = 2 * math.pi * hz
    wd = w0 * math.sqrt(1 - damping * damping)
    env = math.exp(-damping * w0 * t)
    peak = math.atan(wd / (damping * w0)) / wd  # when the impulse response tops out, so `shove` is its peak
    k = 1 / (math.exp(-damping * w0 * peak) * math.sin(wd * peak))
    dx = shove * k * env * math.sin(wd * t)
    d = squash * env * math.cos(1.6 * wd * t)  # squash at contact, then a quicker wobble
    sx = 1 - d
    return dx, sx, 1 / sx


HIT = 1.1                       # seconds: when the ball meets the block
BALL_R, BLOCK_W, BLOCK_H = 46, 150, 230


def draw(n, cv):
    t = n / demo.FPS
    ground = demo.H / 2 + 170
    face = demo.W / 2 + 60       # the block's left face at rest, where the ball strikes
    demo.floor(cv, ground)

    dx, sx, sy = impact(t - HIT, shove=50, squash=0.18, hz=3.0)
    left = face + dx
    w, h = BLOCK_W * sx, BLOCK_H * sy
    cv.rect(left, ground - h, w, h, demo.TEAL, radius=14)       # pressed in from the left, standing on the floor
    cv.mark('block', left, ground - h, w, h)

    if t < HIT:                  # rolling in at a steady clip...
        bx = face - BALL_R - 900 * (HIT - t)
    else:                        # ...then bounced straight back, slowing to a stop
        u = vb.clamp01((t - HIT) / 1.2)
        bx = face - BALL_R - 260 * (1 - (1 - u) ** 3)
    by = ground - BALL_R
    k = n - round(HIT * demo.FPS)
    if 0 <= k < 4:               # a few frames of the ball itself flattened on contact
        cv.ctx.save()
        cv.ctx.translate(face, by)
        cv.ctx.scale(0.8, 1.15)
        demo.dot(cv, -BALL_R, 0, BALL_R)
        cv.ctx.restore()
    else:
        demo.dot(cv, bx, by, BALL_R)
    cv.mark('ball', bx - BALL_R, by - BALL_R, 2 * BALL_R, 2 * BALL_R)

    if 0 <= k < 6:               # short strike marks flying up off the point of contact
        fade = 1 - k / 6
        for a in (-155, -125, -100, -75):
            r = math.radians(a)
            r0, r1 = BALL_R + 16 + 14 * k, BALL_R + 56 + 22 * k
            cv.line(face + r0 * math.cos(r), by + r0 * math.sin(r), face + r1 * math.cos(r),
                    by + r1 * math.sin(r), demo.INK, width=5, alpha=fade)


CAPABILITY = Capability(
    id='impact',
    name='Impact',
    family='principles',
    group='Physics',
    aliases=('collision hit', 'hit reaction'),
    definition='One object strikes another: the striker stops or rebounds at once, and the one it hit '
               'is knocked back, squashes against the blow and wobbles to rest.',
    phrasings=('the ball smacks into the box and the box gets knocked and jiggles',
               'make it hit with a thud and a wobble',
               'show a collision with some recoil'),
    related=('impact-hit', 'hitstop', 'impact-shake', 'elastic-collisions', 'fracture-shatter',
             'badge-stamp-impact'),
    api=('videobuilder.capabilities.principles.impact.impact',),
    demo=lambda: demo.film(draw),
)

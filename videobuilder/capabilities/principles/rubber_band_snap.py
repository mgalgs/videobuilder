"""Rubber Band Snap: something tethered to a point is dragged away from it,
slowing as the band tightens, then let go -- it whips back, flies past where
it started and wobbles to rest. The snap-back is `vb.spring`; this module adds
the pull before it and the timing that joins the two."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rubber_band_snap(t, pull=1.0, hold=0.15, ratio=0.25, hz=2.2):
    """Stretch at `t` seconds: 0 at rest, rising to 1 over `pull` seconds as
    the band is drawn out (fast at first, slowing as the tension grows),
    held at 1 for `hold` seconds, then released -- an under-damped spring
    (`ratio`, `hz` as in `vb.damped`) that swings below 0, past the rest
    point, and settles back to 0. Multiply by the pull offset to place the
    tethered thing."""
    if t <= 0:
        return 0.0
    if t < pull:
        x = t / pull
        return 1 - (1 - x) ** 2
    t -= pull + hold
    if t <= 0:
        return 1.0
    return 1 - vb.spring(t, **vb.damped(ratio, hz))


def draw(n, cv):
    ax, ay = demo.W / 2, 120                       # the anchor pin
    rx, ry = demo.W / 2, 280                       # where the ball hangs at rest
    dx, dy = 230, 180                              # how far it is dragged
    # a slow 1.8 s draw, held to 2.85 s so the gallery's poster (70% in, 2.8 s)
    # catches the band at full stretch; the snap and wobble fill the last 1.15 s
    s = rubber_band_snap(n / demo.FPS - 0.5, pull=1.8, hold=0.55)
    bx, by = rx + dx * s, ry + dy * s
    cv.outline(rx - 30, ry - 30, 60, 60, demo.MUTED, width=2, radius=30, alpha=0.45)  # its resting place
    length = math.hypot(bx - ax, by - ay)
    rest = ry - ay
    tension = max(0.0, length / rest - 1)          # the band thins as it stretches
    cv.line(ax, ay, bx, by, demo.TEAL, width=max(1.5, 7 / (1 + 1.6 * tension)))
    cv.line(ax - 40, ay, ax + 40, ay, demo.MUTED, width=2)
    demo.dot(cv, ax, ay, 8, color=demo.INK)
    demo.dot(cv, bx, by, 30)
    cv.mark('ball', bx - 30, by - 30, 60, 60)


CAPABILITY = Capability(
    id='rubber-band-snap',
    name='Rubber Band Snap',
    family='principles',
    group='Physics',
    aliases=('elastic tether', 'stretch and snap', 'slingshot release'),
    definition='Something tied to a fixed point is dragged away against a tightening band, then let go, '
               'so it whips back, shoots past its resting place and wobbles to a stop.',
    phrasings=('pull it back on an elastic and let it fly home',
               'stretch it out like a slingshot, then let it snap back',
               'drag it away and have it spring back past where it started'),
    related=('elastic-stretch', 'rubber-band-overscroll', 'elastic-ease-out', 'squash-on-tap',
             'elastic-ease-in', 'elastic-horizontal-squash'),
    api=('videobuilder.capabilities.principles.rubber_band_snap.rubber_band_snap', 'videobuilder.spring',
         'videobuilder.damped'),
    demo=lambda: demo.film(draw, seconds=4.0),
)

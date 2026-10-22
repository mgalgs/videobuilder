"""Swipe to Dismiss: a card tracks a finger sideways; let go short of the
threshold and it springs home, let go past it and it flies off the edge."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SNAP = vb.damped(0.45, hz=2.2)   # the spring home: one soft overshoot


def swipe_offset(t, distance, threshold, off, pull=0.5, fly=0.35, spring=SNAP):
    """The card's sideways offset `t` seconds after the finger grabs it, and
    whether this swipe dismisses it. The finger drags it out to `distance` px
    (signed: negative is leftwards) over `pull` seconds and lets go. If
    `abs(distance) >= threshold` the card keeps going, accelerating out to
    `off` px (on that side) in `fly` seconds; otherwise it springs back to 0
    with `spring` (params for `vb.spring`). Returns `(x, dismissed)`."""
    dismissed = abs(distance) >= threshold
    if t <= 0:
        return 0.0, dismissed
    if t < pull:
        return distance * vb.ease_out_quint(t / pull), dismissed
    after = t - pull
    if dismissed:
        q = vb.clamp01(after / fly)
        # Leaves at the finger's speed and speeds up: quadratic plus a linear start.
        end = math.copysign(off, distance)
        return distance + (end - distance) * (0.35 * q + 0.65 * q * q), dismissed
    return distance * (1 - vb.spring(after, **spring)), dismissed


def draw_swiped(cv, draw, cx, cy, x, off, tilt=10.0, fade=0.6):
    """Draw `draw(cv)` -- a card centred at (cx, cy) -- shifted `x` px sideways,
    leaning up to `tilt` degrees the way it's going (pivoting on a point well
    below it, like a card held at the bottom) and fading by up to `fade` as
    `abs(x)` reaches `off`."""
    k = vb.clamp01(abs(x) / off)
    c = cv.ctx
    pivot = cy + 900
    with cv.layer(opacity=1 - fade * k):
        c.save()
        c.translate(cx + x, pivot)
        c.rotate(math.radians(tilt) * max(-1.0, min(1.0, x / off)))
        c.translate(-cx, -pivot)
        try:
            draw(cv)
        finally:
            c.restore()


def finger(cv, x, y, pressed):
    """A touch point: a soft ring with a dot, smaller and fuller while pressed."""
    r = 30 - 6 * pressed
    demo.dot(cv, x, y, r + 14, demo.INK, alpha=0.10 + 0.12 * pressed)
    demo.dot(cv, x, y, r, demo.INK, alpha=0.35 + 0.4 * pressed)


CX, CY = demo.W / 2, demo.H / 2
CARD_W, CARD_H = 560, 320
THRESHOLD = 300
OFF = demo.W / 2 + CARD_W
# Two tries: a short drag that springs back, then a long one that dismisses.
TRIES = ((0.25, 180), (1.45, 440))
PULL = 0.5


def draw(n, cv):
    t = n / demo.FPS
    gone = demo.phase(n, TRIES[1][0] + PULL, TRIES[1][0] + PULL + 0.5)
    # The next card waits underneath and rises to take the front once the top one goes.
    under = vb.ease_out_quint(gone)
    demo.card(cv, CX, CY + 26 * (1 - under), CARD_W, CARD_H, color=demo.TEAL,
              scale=0.92 + 0.08 * under, alpha=0.55 + 0.45 * under)
    start, distance = TRIES[0] if t < TRIES[1][0] else TRIES[1]
    x, _ = swipe_offset(t - start, distance, THRESHOLD, OFF, pull=PULL)
    draw_swiped(cv, lambda c: demo.card(c, CX, CY, CARD_W, CARD_H), CX, CY, x, OFF)
    # The finger lands, drags, lifts.
    hold = t - start
    if -0.15 < hold < PULL + 0.25:
        down = vb.clamp01((hold + 0.15) / 0.15) * vb.clamp01((PULL + 0.25 - hold) / 0.25)
        fx = CX + 60 + distance * vb.ease_out_quint(vb.clamp01(hold / PULL))
        if hold > PULL:
            fx += (hold - PULL) * 300
        with cv.layer(opacity=down):
            finger(cv, fx, CY + 40, 1.0 if 0 <= hold <= PULL else 0.0)


CAPABILITY = Capability(
    id='swipe-to-dismiss',
    name='Swipe to dismiss',
    family='ui',
    group='Gestures & drag',
    aliases=('swipe away', 'flick dismiss', 'swipe to delete'),
    definition='A card slides sideways under a dragging finger and, once let go, either springs back '
               'to its place or, if pushed far enough, keeps going and leaves the screen.',
    phrasings=('drag the notification off to the side to get rid of it',
               'the card snaps back if you do not pull it far enough, but flies away if you do',
               'flick the card off screen like clearing an alert on a phone'),
    related=('stacked-card-reveal', 'flip', 'sticky-card-stack-on-scroll', 'uncover',
             'toast-auto-dismiss-bar', 'end-card-with-subscribe-slot'),
    api=('videobuilder.capabilities.ui.swipe_to_dismiss.swipe_offset',
         'videobuilder.capabilities.ui.swipe_to_dismiss.draw_swiped'),
    demo=lambda: demo.film(draw),
)

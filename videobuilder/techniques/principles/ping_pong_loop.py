"""Ping-Pong Loop: an animation plays forwards to its end, then plays the same
motion backwards to its start, and repeats -- a loop with no jump cut."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ping_pong(t, period, ease=vb.linear, offset=0.0):
    """Progress 0 -> 1 -> 0 at time `t` (seconds, or frames if `period` is in
    frames): forwards for the first half of each `period`, backwards for the
    second, repeating forever. `ease` shapes each leg, so the reverse leg is
    the forward leg played backwards. `offset` shifts the cycle (in the same
    units as `t`), e.g. to stagger several things looping together."""
    x = ((t + offset) / period) % 1.0
    return ease(1 - abs(2 * x - 1))


def direction(t, period, offset=0.0):
    """+1 while `ping_pong` is playing forwards at `t`, -1 while it plays backwards."""
    return 1 if ((t + offset) / period) % 1.0 < 0.5 else -1


PERIOD = 1.5  # seconds for one there-and-back: two full loops in the demo


def _chevron(cv, cx, cy, d, color, alpha=1.0, s=16):
    cv.line(cx - d * s / 2, cy - s, cx + d * s / 2, cy, color, width=5, alpha=alpha)
    cv.line(cx + d * s / 2, cy, cx - d * s / 2, cy + s, color, width=5, alpha=alpha)


def draw(n, cv):
    t = n / demo.FPS
    x0, x1, y = demo.W / 2 - 290, demo.W / 2 + 290, demo.H / 2 - 50
    for x in (x0, x1):  # the two ends the motion turns around at
        cv.outline(x - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)
    for k in range(1, 6):  # a short trail behind the card shows which way it is going
        p = ping_pong(t - k * 0.035, PERIOD, vb.ease_in_out_quart)
        demo.card(cv, x0 + (x1 - x0) * p, y, alpha=0.12 * (6 - k) / 5)
    p = ping_pong(t, PERIOD, vb.ease_in_out_quart)
    demo.card(cv, x0 + (x1 - x0) * p, y)

    # the playhead: runs along the timeline and bounces back off each end
    ty, d = demo.H - 130, direction(t, PERIOD)
    cv.line(x0, ty, x1, ty, demo.LINE, width=6)
    for x in (x0, x1):
        cv.line(x, ty - 18, x, ty + 18, demo.MUTED, width=4)
    head = x0 + (x1 - x0) * ping_pong(t, PERIOD)
    cv.line(x0, ty, head, ty, demo.TEAL, width=6)
    demo.dot(cv, head, ty, 14, demo.TEAL)
    label = 'forward' if d > 0 else 'reverse'
    demo.word(cv, label, demo.W / 2, ty + 55, size=34, color=demo.INK if d > 0 else demo.TEAL, weight=700)
    pulse = 0.5 + 0.5 * math.cos(2 * math.pi * t / 0.5)
    _chevron(cv, demo.W / 2 + d * 100, ty + 55, d, demo.TEAL, alpha=0.5 + 0.5 * pulse)


TECHNIQUE = Technique(
    id='ping-pong-loop',
    name='Ping-Pong Loop',
    family='principles',
    group='Cycles & loops',
    aliases=('yoyo', 'boomerang loop', 'back-and-forth loop', 'palindrome loop', 'alternate loop'),
    definition='An animation that plays through to its end, then runs the same motion in reverse back '
               'to its start, over and over, so the loop never jumps.',
    phrasings=('play it forwards then backwards on repeat',
               'make it swing back and forth like a boomerang',
               'loop it so it rewinds instead of snapping back to the start'),
    related=('interruptible-motion', 'reverse-playback', 'delay', 'frame-by-frame-hand-drawn-animation',
             'empty-state-idle-loop', 'wiggle-path'),
    api=('videobuilder.techniques.principles.ping_pong_loop.ping_pong',
         'videobuilder.techniques.principles.ping_pong_loop.direction'),
    demo=lambda: demo.film(draw),
)

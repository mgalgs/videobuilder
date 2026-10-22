"""Oscillation: a value that swings back and forth around a rest point on a
sine wave, steadily or dying away, for anything that sways, bobs or pulses."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def oscillate(t, amplitude=1.0, hz=1.0, phase=0.0, decay=0.0):
    """Offset from rest at time `t` seconds: a sine of `amplitude` at `hz`
    swings a second, starting `phase` turns in (0.25 starts at the peak).
    `decay` > 0 shrinks the swing by a factor of e every 1/`decay` seconds,
    so the motion settles; 0 keeps it going forever."""
    return amplitude * math.sin(2 * math.pi * (hz * t + phase)) * math.exp(-decay * max(t, 0.0))


AMP, HZ = 300, 1.0
TOP, BOTTOM = 190, demo.H - 120      # the pen's row, and the bottom of the trace it leaves
PX_PER_S = 150                       # the trace scrolls down this fast, so time reads top to bottom


def draw(n, cv):
    cx, t = demo.W / 2, n / demo.FPS
    for x in (cx - AMP, cx + AMP):                       # the two extremes it swings between
        cv.line(x, TOP - 60, x, BOTTOM, demo.MUTED, width=2, alpha=0.35)
    cv.line(cx, TOP - 60, cx, BOTTOM, demo.MUTED, width=2, alpha=0.6)  # rest
    pts = []                                             # its history, a sine wave trailing below it
    for k in range(0, n + 1):
        y = TOP + (t - k / demo.FPS) * PX_PER_S
        if y > BOTTOM:
            continue
        pts.append((cx + oscillate(k / demo.FPS, AMP, HZ), y))
    if len(pts) > 1:
        vb.paths.draw(cv, pts, demo.TEAL, width=5, alpha=0.85)
    x, r = cx + oscillate(t, AMP, HZ), 38
    demo.dot(cv, x, TOP, r)
    cv.mark('dot', x - r, TOP - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='oscillation',
    name='Oscillation',
    family='principles',
    group='Physics',
    aliases=('oscillate', 'sine motion', 'back and forth', 'sway', 'harmonic motion'),
    definition='Something swings to and fro around a resting point in a smooth, regular rhythm, '
               'like a pendulum or a weight on a spring.',
    phrasings=('make it sway back and forth like a pendulum',
               'have the dot swing side to side on a smooth wave',
               'bob it up and down in a steady rhythm'),
    related=('sine-wave-text', 'sine-wave-distortion', 'wave-stagger', 'wave-deformer', 'ocean-waves',
             'ease-out-sine'),
    api=('videobuilder.capabilities.principles.oscillation.oscillate',),
    demo=lambda: demo.film(draw),
)

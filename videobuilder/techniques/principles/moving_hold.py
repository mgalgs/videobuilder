"""Moving Hold: a subject that has come to rest keeps a small, slow, never-
repeating drift -- a breath of scale, a wander of a few pixels, a hair of
tilt -- so the hold reads as alive rather than as a frozen frame."""
import math
from collections import namedtuple

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

Hold = namedtuple('Hold', 'dx dy scale angle')


def moving_hold(t, drift=8.0, breathe=0.015, tilt=0.6, period=2.6, settle=0.4, seed=0):
    """The offsets to apply to a held subject `t` seconds into its hold:
    `Hold(dx, dy, scale, angle)` -- px to add to its position, a factor to
    scale it by about its centre, and radians to rotate it by. `drift`: px
    of wander; `breathe`: share of size it swells by; `tilt`: degrees of
    sway; `period`: seconds per slow breath (the wander uses incommensurate
    rates, so it never visibly loops). The motion fades in over `settle`
    seconds, so it picks up smoothly from the move that arrived; `seed`
    gives two held things different drifts. At `t <= 0` it is all zero."""
    if t <= 0:
        return Hold(0.0, 0.0, 1.0, 0.0)
    k = vb.clamp01(t / settle) if settle > 0 else 1.0
    k = k * k * (3 - 2 * k)
    w = 2 * math.pi / period
    ph = seed * 1.7
    sx = 0.65 * math.sin(w * 0.61 * t + ph) + 0.35 * math.sin(w * 1.37 * t + 2.1 + ph)
    sy = 0.6 * math.sin(w * 0.47 * t + 1.3 + ph) + 0.4 * math.sin(w * 1.13 * t + 0.4 + ph)
    sa = math.sin(w * 0.53 * t + 0.9 + ph)
    return Hold(k * drift * sx, k * drift * sy, 1 + k * breathe * math.sin(w * t + ph),
                k * math.radians(tilt) * sa)


ARRIVE = (0.2, 0.9)  # the card slides in, then holds for the rest of the demo


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    p = vb.ease_out_quint(demo.phase(n, *ARRIVE))
    x = cx - 520 * (1 - p)
    h = moving_hold(n / demo.FPS - ARRIVE[1], drift=12, breathe=0.03, tilt=1.4, period=1.6)
    cv.outline(cx - 130, cy - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it came to rest
    cv.ctx.save()
    cv.ctx.translate(x + h.dx, cy + h.dy)
    cv.ctx.rotate(h.angle)
    demo.card(cv, 0, 0, scale=h.scale)
    cv.ctx.restore()


TECHNIQUE = Technique(
    id='moving-hold',
    name='Moving Hold',
    family='principles',
    group='Principle sub-techniques',
    aliases=('breathing hold', 'slight drift hold', 'living hold'),
    definition='Once something has stopped, it keeps up a faint, slow drift and swell so the pause '
               'feels alive instead of looking like a paused frame.',
    phrasings=('holds still but keeps gently breathing',
               'stops but still floats a tiny bit so it never looks frozen',
               'keep a little life in it while it sits there'),
    related=('freeze-frame', 'breathing-idle', 'settle', 'push-in', 'handheld-shake', 'momentum-fling'),
    api=('videobuilder.techniques.principles.moving_hold.moving_hold',),
    demo=lambda: demo.film(draw),
)

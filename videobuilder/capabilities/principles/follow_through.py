"""Follow Through: a loose part riding on a moving body trails behind it while
it moves, then swings on past when the body stops and settles back to rest."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def follow_through(path, t, hz=1.6, ratio=0.22, step=1 / 240):
    """Where a loose part attached to a body is at `t` seconds, given `path(t)`,
    the body's position (any scalar: x, y, an angle). The part is a damped
    spring chasing the body: it lags while the body moves, overshoots when the
    body stops, and settles on it. `hz` is how fast it swings, `ratio` its
    damping (lower swings longer). Integrated from rest at `t = 0` in fixed
    steps, so any frame evaluates alone. `follow_through(...) - path(t)` is the
    part's offset from the body, e.g. to bend an antenna or a tail by."""
    k = (2 * math.pi * hz) ** 2
    c = 2 * ratio * math.sqrt(k)
    x, v, s = path(0.0), 0.0, 0.0
    while s < t:
        h = min(step, t - s)
        s += h
        v += (k * (path(s) - x) - c * v) * h
        x += v * h
    return x


X0, X1, START, STOP = 300, demo.W - 300, 0.3, 1.4
R, STALK = 46, 190


def body_x(t):
    return X0 + (X1 - X0) * vb.ease_in_out_quart(vb.clamp01((t - START) / (STOP - START)))


def draw(n, cv):
    t = n / demo.FPS
    ground = demo.H / 2 + 160
    bx, by = body_x(t), ground - R
    lag = follow_through(body_x, t) - bx                       # < 0 trailing, > 0 overshooting
    a = max(-1.2, min(1.2, math.atan2(lag, STALK) * 1.6))      # lean of the stalk from upright
    base = (bx, by - R + 4)
    tip = (bx + STALK * math.sin(a), base[1] - STALK * math.cos(a))
    bend = (bx, base[1] - STALK * 0.55)                         # stiff at the root, loose at the tip
    demo.floor(cv, ground)
    c = cv.ctx
    c.new_path()
    c.move_to(*base)
    c.curve_to(*bend, *bend, *tip)
    c.set_source_rgba(*vb.canvas.rgba(demo.TEAL))
    c.set_line_width(10)
    c.set_line_cap(1)  # round
    c.stroke()
    demo.dot(cv, *tip, r=14, color=demo.INK)
    demo.dot(cv, bx, by, R)
    cv.mark('body', bx - R, by - R, 2 * R, 2 * R)


CAPABILITY = Capability(
    id='follow-through',
    name='Follow Through',
    family='principles',
    group='Classic principles',
    aliases=('follow-through', 'drag and follow-through', 'overlapping action'),
    definition='When a moving thing comes to a stop, its loose bits (a tail, hair, an antenna) '
               'carry on past it, swing back and settle a beat later.',
    phrasings=('it stops but the antenna keeps wobbling',
               'make the tail lag behind and swing past when it halts',
               'the floppy parts should keep going after the body stops'),
    related=('chain-follow-through', 'tracking-shot', 'path-follow-motion', 'fly-through', 'cut-on-action',
             'dolly-in-and-out'),
    api=('videobuilder.capabilities.principles.follow_through.follow_through',),
    demo=lambda: demo.film(draw),
)

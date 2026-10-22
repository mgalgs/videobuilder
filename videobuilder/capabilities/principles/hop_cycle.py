"""Hop Cycle: a body that hops in place over and over -- it crouches into the
floor, springs up stretched tall, rounds out at the top of its arc, falls
stretched again and squashes as it lands into the next crouch."""
import math
from collections import namedtuple

from .. import _demo as demo
from ..schema import Capability

Hop = namedtuple('Hop', 'lift sx sy')
Hop.__doc__ = """One moment of a hop: `lift` is the height off the floor as a
fraction of the hop's peak (0 on the floor, 1 at the top); `sx`, `sy` scale the
body about its base (squashed wide on the floor, stretched tall in the air)."""


def hop_cycle(u, ground=0.35, squash=0.3, stretch=0.2):
    """The pose `u` cycles into a looping hop (any real `u`; it wraps every 1).

    Each cycle spends `ground` of its length on the floor -- landing, sinking
    into a squash `squash` deep at the middle, and pushing off -- then the rest
    in the air on a parabola. Airborne, the body stretches by up to `stretch`
    in proportion to its speed, so it is tallest at takeoff and landing and
    round at the top. Width is `1 / sy`, keeping the body's area. A film
    drives it with `hop_cycle(seconds / period)`."""
    u %= 1.0
    if u < ground:                                   # on the floor: land, squash, push off
        w = u / ground
        sy = 1 + stretch - (stretch + squash) * math.sin(math.pi * w)
        lift = 0.0
    else:                                            # in the air: up and back down
        s = (u - ground) / (1 - ground)
        lift = 4 * s * (1 - s)
        sy = 1 + stretch * abs(1 - 2 * s)
    return Hop(lift, 1 / sy, sy)


PERIOD = 0.9   # seconds a hop
R = 32


def draw(n, cv):
    ground, peak = demo.H - 110, 220
    h = hop_cycle(n / demo.FPS / PERIOD + 0.2)      # start mid-crouch, just before the first push-off
    rx, ry = R * h.sx, R * h.sy
    cx, cy = demo.W / 2, ground - ry - peak * h.lift
    cv.ctx.save()                                    # the shadow shrinks and fades as it rises
    cv.ctx.translate(demo.W / 2, ground + 4)
    cv.ctx.scale(1, 0.2)
    demo.dot(cv, 0, 0, rx * (1.1 - 0.5 * h.lift), color='#000000', alpha=0.5 - 0.35 * h.lift)
    cv.ctx.restore()
    demo.floor(cv, ground)
    cv.ctx.save()
    cv.ctx.translate(cx, cy)
    cv.ctx.scale(h.sx, h.sy)
    demo.dot(cv, 0, 0, R)
    cv.ctx.restore()
    cv.mark('ball', cx - rx, cy - ry, 2 * rx, 2 * ry)


CAPABILITY = Capability(
    id='hop-cycle',
    name='Hop Cycle',
    family='principles',
    group='Cycles & loops',
    aliases=('hopping loop', 'bounce cycle', 'jump cycle'),
    definition='A looping hop in place: the body crouches and squashes, springs up stretched, rounds out '
               'at the top, then falls and squashes on landing to start the next hop.',
    phrasings=('make it keep hopping up and down on the spot',
               'a little bouncing loop with squash and stretch',
               'have the ball jump over and over like it is excited'),
    related=('steps-easing', 'rotating-polygon-loop', 'geometric-loop', 'cyclic-cellular-automaton',
             'hopalong-attractor', 'cycle-diagram-rotation'),
    api=('videobuilder.capabilities.principles.hop_cycle.hop_cycle',),
    demo=lambda: demo.film(draw),
)

"""Squash and Stretch: a body that gets longer along its line of travel while
it moves fast and flattens out when it hits something, giving back across
what it takes along so it seems to keep its volume."""
import math
from contextlib import contextmanager

from .. import _demo as demo
from ..schema import Capability


def squash_stretch_scale(amount, limit=0.6):
    """(along, across) scale factors for a deformation of `amount`: positive
    stretches along the axis of motion, negative squashes it, 0 is the rest
    shape. `along * across == 1`, so the area stays the same. `amount` is
    clamped to +-`limit`."""
    along = 1 + max(-limit, min(limit, amount))
    return along, 1 / along


@contextmanager
def squash_stretch(cv, ax, ay, amount, angle=math.pi / 2, limit=0.6):
    """Deform whatever is drawn inside the block about the anchor (ax, ay):
    stretched (`amount` > 0) or squashed (< 0) along `angle` (radians,
    canvas-style: 0 points right, pi/2 points down), with the area kept.
    Draw in ordinary frame coordinates inside it. Anchor a landing at the
    contact point, so the body flattens onto the floor rather than into it;
    anchor flight at the centre.

        with squash_stretch(cv, x, floor_y, -0.4):     # flattened on the floor
            demo.dot(cv, x, floor_y - r, r)
    """
    along, across = squash_stretch_scale(amount, limit)
    c = cv.ctx
    c.save()
    c.translate(ax, ay)
    c.rotate(angle)
    c.scale(along, across)
    c.rotate(-angle)
    c.translate(-ax, -ay)
    try:
        yield
    finally:
        c.restore()


# The demo: a ball dropped onto a floor, bouncing three times. In the air it
# stretches in proportion to its speed; on each landing it stays on the floor
# for several frames and flattens, harder the faster it came in, holding near
# its flattest for most of the contact. The drop is timed so the second
# landing is at its flattest on the gallery's poster frame (70% through).
R, DROP, G, RESTITUTION = 34, 320.0, 1750.0, 0.55
STRETCH, SQUASH = 0.32, 0.5     # most stretch in flight, most squash on the hardest landing
POSTER = int(round(demo.SECONDS * demo.FPS) * 0.7) / demo.FPS   # the poster frame, picked as the gallery picks it


def _bounces(start=0.0):
    """(start, kind, length, v) phases: 'fall' from rest, 'contact' at impact
    speed `v`, 'hop' launched at `v`. The last landing settles into 'rest'
    rather than launching a hop too small to read."""
    v0 = v = math.sqrt(2 * G * DROP)
    t, out = start, [(start, 'fall', v / G, v)]
    t += v / G
    while True:
        contact = 0.08 + 0.12 * v / v0
        out.append((t, 'contact', contact, v))
        t += contact
        v *= RESTITUTION
        if v <= 130:
            break
        out.append((t, 'hop', 2 * v / G, v))
        t += 2 * v / G
    out.append((t, 'rest', 99.0, 0.0))
    return out


_second = [p for p in _bounces() if p[1] == 'contact'][1]
START = POSTER - (_second[0] + _second[2] / 2)

PHASES = _bounces(START)
V0 = PHASES[0][3]


def ball(t):
    """(height of the ball's bottom above the floor, deformation) at `t` seconds."""
    if t < START:
        return DROP, 0.0
    for t0, kind, length, v in PHASES:
        if t0 <= t < t0 + length:
            s = t - t0
            if kind == 'fall':
                return DROP - G * s * s / 2, STRETCH * G * s / V0
            if kind == 'hop':
                return v * s - G * s * s / 2, STRETCH * abs(v - G * s) / V0
            if kind == 'contact':
                return 0.0, -SQUASH * (v / V0) * math.sin(math.pi * s / length) ** 0.5
    return 0.0, 0.0


def draw(n, cv):
    ground, x = demo.H - 80, demo.W / 2
    h, amount = ball(n / demo.FPS)
    near = 1 - h / DROP
    cv.ctx.save()
    cv.ctx.translate(x, ground + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, R * (0.6 + 0.7 * near), color='#000000', alpha=0.12 + 0.35 * near)
    cv.ctx.restore()
    demo.floor(cv, ground)
    bottom = ground - h
    anchor = bottom if h <= 0 else bottom - R   # flatten onto the floor; stretch about the centre in flight
    with squash_stretch(cv, x, anchor, amount):
        demo.dot(cv, x, bottom - R, R)
    along, across = squash_stretch_scale(amount)
    top = anchor - 2 * R * along if h <= 0 else anchor - R * along
    cv.mark('ball', x - R * across, top, 2 * R * across, 2 * R * along)


CAPABILITY = Capability(
    id='squash-and-stretch',
    name='Squash and Stretch',
    family='principles',
    group='Disney principles',
    aliases=('squash & stretch', 'volume squash'),
    definition='A moving body grows long and thin along its path while it travels fast and goes short and '
               'wide when it lands, trading width for height so it seems to hold the same amount of stuff.',
    phrasings=('make the ball flatten when it hits the ground and stretch out as it falls',
               'give it some rubbery squish when it lands',
               'stretch it while it flies and splat it on impact'),
    related=('elastic-horizontal-squash', 'squash-on-tap', 'volume-preservation', 'elastic-ease-out',
             'elastic-stretch', 'rubber-band-overscroll'),
    api=('videobuilder.capabilities.principles.squash_and_stretch.squash_stretch',
         'videobuilder.capabilities.principles.squash_and_stretch.squash_stretch_scale'),
    demo=lambda: demo.film(draw),
)

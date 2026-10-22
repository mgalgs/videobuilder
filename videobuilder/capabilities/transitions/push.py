"""Push: the incoming scene slides in from one edge and shoves the outgoing
scene out of the opposite edge, the two locked together as they move."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

DIRECTIONS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}


def push(cv, a, b, p, direction='left', ease=vb.ease_in_out_quart):
    """Draw the push at progress `p` (0 -> 1): `a(cv)` and `b(cv)` side by
    side, travelling one frame's width (or height) together towards
    `direction` ('left', 'right', 'up' or 'down'), so `b` enters from the
    opposite edge exactly as `a` leaves. `ease` shapes the travel.

    In a film, call it while two shots are live in an overlap, e.g.
    `push(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if direction not in DIRECTIONS:
        raise ValueError(f'push: direction must be one of {", ".join(DIRECTIONS)}, not {direction!r}')
    ux, uy = DIRECTIONS[direction]
    w, h = cv.width, cv.height
    t = ease(vb.clamp01(p))
    ax, ay = ux * w * t, uy * h * t
    bx, by = ax - ux * w, ay - uy * h
    with cv.clip(0, 0, w, h):
        with cv.clip(ax, ay, w, h), cv.layer(dx=ax, dy=ay):
            a(cv)
        with cv.clip(bx, by, w, h), cv.layer(dx=bx, dy=by):
            b(cv)


CAPABILITY = Capability(
    id='push',
    name='Push',
    family='transitions',
    group='Slides and Pushes',
    aliases=('slide push', 'shove', 'push slide'),
    definition='The next scene slides in from one side and shoves the current one out the other side, '
               'the two moving together as a single strip.',
    phrasings=('have the new shot push the old one off screen',
               'slide the next scene in and knock the last one out sideways',
               'shove the first frame out of the way with the second'),
    related=('push-in', 'roll-up', 'corner-wipe', 'zoom-through', 'cut-on-action', 'zoom-out-reveal'),
    api=('videobuilder.capabilities.transitions.push.push',),
    demo=lambda: demo.two_scenes(push),
)

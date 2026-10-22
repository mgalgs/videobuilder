"""Linear wipe: a hard, straight edge travels across the frame in one
direction; the incoming scene is on the side it has passed, the outgoing
scene on the side it has yet to reach."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

DIRECTIONS = ('left', 'right', 'up', 'down')


def linear_wipe(cv, a, b, p, direction='right', ease=vb.ease_in_out_quart):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` clipped to the part of the frame the edge has crossed. The edge
    travels toward `direction` ('right' starts at the left side and moves
    right; 'up' starts at the bottom), with `ease` shaping its speed (pass
    `vb.linear` for a constant one). The edge is a clean cut, nothing drawn
    on it.

    In a film, call it while two shots are live in an overlap, e.g.
    `linear_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if direction not in DIRECTIONS:
        raise ValueError(f'linear_wipe: direction must be one of {", ".join(DIRECTIONS)}, not {direction!r}')
    w, h = cv.width, cv.height
    q = ease(vb.clamp01(p))
    a(cv)
    if q <= 0:
        return
    box = {'right': (0, 0, w * q, h),
           'left': (w * (1 - q), 0, w * q, h),
           'down': (0, 0, w, h * q),
           'up': (0, h * (1 - q), w, h * q)}[direction]
    with cv.clip(*box):
        b(cv)


CAPABILITY = Capability(
    id='linear-wipe',
    name='Linear wipe',
    family='transitions',
    group='Wipes',
    aliases=('edge wipe', 'straight wipe', 'line wipe'),
    definition='A single straight, sharp line slides from one side of the frame to the other, '
               'and the new scene takes over everything the line has already passed.',
    phrasings=('wipe the next shot in from the left',
               'swap scenes with a hard edge sliding across the screen',
               'push a straight line across to uncover the new picture'),
    related=('wipe-reveal', 'paint-brush-wipe', 'area-fill-sweep', 'roll-up', 'ribbon-sweep',
             'fill-sweep-button'),
    api=('videobuilder.capabilities.transitions.linear_wipe.linear_wipe',),
    demo=lambda: demo.two_scenes(linear_wipe),
)

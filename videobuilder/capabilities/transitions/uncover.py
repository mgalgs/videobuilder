"""Uncover: the outgoing scene slides off the frame like a card being pulled
away, and the incoming scene is already sitting still underneath it -- the
reverse of a cover, where the new scene slides in over the old one."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

_DIRECTIONS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}


def uncover(cv, a, b, p, direction='left', ease=vb.ease_in_out_quart, shadow=0.5):
    """Draw the uncover at progress `p` (0 -> 1): `b(cv)` fixed in place, and
    `a(cv)` on top of it moved off the frame towards `direction` (`'left'`,
    `'right'`, `'up'` or `'down'`) along `ease`. `shadow` is the opacity of
    the soft shadow `a` casts on `b` as it lifts off (0 for none).

    In a film, call it while two shots are live in an overlap, e.g.
    `uncover(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames, 'up')`."""
    dx, dy = _DIRECTIONS[direction]
    w, h = cv.width, cv.height
    t = ease(vb.clamp01(p))
    ox, oy = dx * w * t, dy * h * t
    b(cv)
    if shadow > 0:
        cv.shadow(ox, oy, w, h, blur=48, spread=4, color=(0, 0, 0, shadow))
    with cv.layer(dx=ox, dy=oy), cv.clip(0, 0, w, h):  # `a` stays a frame-sized card as it moves
        a(cv)


TECHNIQUE = Technique(
    id='uncover',
    name='Uncover',
    family='transitions',
    group='Slides and Pushes',
    aliases=('reveal slide', 'slide off', 'pull away'),
    definition='The current scene slides out of frame in one direction, revealing the next scene, '
               'which was waiting motionless underneath it.',
    phrasings=('slide the old shot away to show the new one behind it',
               'pull the first scene off the screen like a card to reveal the next',
               'the opposite of a cover: the top slide moves out of the way'),
    related=('roll-up', 'corner-wipe', 'zoom-out-reveal', 'fade-up-scroll-reveal', 'zoom-through',
             'device-mockup-slide-in'),
    api=('videobuilder.techniques.transitions.uncover.uncover',),
    demo=lambda: demo.two_scenes(uncover),
)

"""Slide-over cover: the outgoing scene stays put while the incoming scene
slides in from one edge on top of it, until the new scene covers the frame."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_DIRECTIONS = {'left': (1, 0), 'right': (-1, 0), 'up': (0, 1), 'down': (0, -1)}


def slide_over_cover(cv, a, b, p, direction='left', ease=vb.ease_in_out_quart, shadow=0.5):
    """Draw the cover at progress `p` (0 -> 1): `a(cv)` held still, with
    `b(cv)` sliding over it from the edge opposite `direction` (`'left'`
    means b travels leftwards, entering from the right) until it fills the
    frame. `shadow` is the opacity of the soft shadow b's leading edge casts
    on a (0 for none).

    In a film, call it while two shots are live in an overlap, e.g.
    `slide_over_cover(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    sx, sy = _DIRECTIONS[direction]
    w, h = cv.width, cv.height
    t = ease(vb.clamp01(p))
    dx, dy = sx * w * (1 - t), sy * h * (1 - t)
    a(cv)
    if shadow > 0 and 0 < t < 1:
        cv.shadow(dx, dy, w, h, blur=48, spread=4, color=(0, 0, 0, shadow))
    with cv.clip(max(dx, 0), max(dy, 0), w - abs(dx), h - abs(dy)):
        with cv.layer(dx=dx, dy=dy):
            b(cv)


CAPABILITY = Capability(
    id='slide-over-cover',
    name='Slide-over cover',
    family='transitions',
    group='Slides and Pushes',
    aliases=('cover', 'slide over', 'new slide over'),
    definition='The next scene glides in from one side and lays itself on top of the current scene, '
               'which stays perfectly still underneath until it is hidden.',
    phrasings=('slide the next slide in over the top of this one',
               'have the new scene come in from the side and cover the old one',
               'like dealing a card on top of the last one, keep the first scene still'),
    related=('roll-up', 'corner-wipe', 'coverflow-carousel', 'zoom-out-reveal', 'zoom-through', 'tumble'),
    api=('videobuilder.capabilities.transitions.slide_over_cover.slide_over_cover',),
    demo=lambda: demo.two_scenes(slide_over_cover, start=1.35, length=1.4),
)

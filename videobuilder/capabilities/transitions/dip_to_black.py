"""Dip to Black: the outgoing scene fades to black, black holds a beat, then
the incoming scene fades up from it."""
from .. import _demo as demo
from ..schema import Capability


def dip_to_black(cv, a, b, p, hold=0.2, color='#000000'):
    """Draw the dip at progress `p` (0 -> 1): `a(cv)` fading out to `color`,
    `color` alone for the middle `hold` fraction, then `b(cv)` fading up.

    In a film, call it while two shots are live in an overlap, e.g.
    `dip_to_black(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    fade = (1 - hold) / 2
    if p < fade:
        a(cv)
        cv.fill(color, alpha=p / fade)
    elif p < fade + hold:
        cv.fill(color)
    else:
        b(cv)
        cv.fill(color, alpha=max(0.0, 1 - (p - fade - hold) / fade))


CAPABILITY = Capability(
    id='dip-to-black',
    name='Dip to Black',
    family='transitions',
    group='Dissolves',
    aliases=('fade through black', 'fade out, fade in'),
    definition='The picture fades all the way down to black, stays black for a moment, '
               'then the next scene fades up out of it.',
    phrasings=('fade to black and back in on the next scene',
               'go dark for a second between the two scenes',
               'a soft fade out, then a fade in'),
    related=('dip-to-white', 'cross-dissolve', 'fade-in-from-black'),
    api=('videobuilder.capabilities.transitions.dip_to_black.dip_to_black',),
    demo=lambda: demo.two_scenes(dip_to_black),
)

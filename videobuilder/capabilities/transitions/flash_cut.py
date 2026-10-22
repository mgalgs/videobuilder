"""White flash transition: the outgoing scene blows out to white in a few
frames, the cut happens under the white, and the incoming scene burns back
in as the flash decays.

A timeline does the same between two clips with `"transition": "flash"`
(see `videobuilder/assembly.py`); this is the canvas version, for a cut
between two scenes a film draws itself."""
from .. import _demo as demo
from ..schema import Capability


def flash_cut(cv, a, b, p, rise=0.25, hold=0.1, color='#ffffff'):
    """Draw the flash at progress `p` (0 -> 1): `a(cv)` washing up to `color`
    over the first `rise` fraction, `color` alone for `hold`, then `b(cv)`
    coming back out of it over the rest. The rise is fast and the decay
    slower and eased, the way an overexposed frame bleeds off.

    In a film, call it while two shots are live in a short overlap (a third
    to half a second reads as a flash, longer as a fade), e.g.
    `flash_cut(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if p < rise:
        a(cv)
        cv.fill(color, alpha=(p / rise) ** 2)
    elif p < rise + hold:
        cv.fill(color)
    else:
        b(cv)
        k = (p - rise - hold) / (1 - rise - hold)
        cv.fill(color, alpha=max(0.0, 1 - k) ** 2)


CAPABILITY = Capability(
    id='flash-cut',
    name='White flash transition',
    family='transitions',
    group='Light and Flash',
    aliases=('flash cut', 'white flash', 'flash frame', 'flash transition', 'exposure flash',
             'overexposure flash'),
    definition='The frame blows out to bright white for an instant, the shot changes underneath, '
               'and the new scene settles back in as the glare fades.',
    phrasings=('flash to white between the two shots',
               'a quick white pop that cuts to the next scene',
               'make it look like a camera flash goes off on the cut'),
    related=('glitch-transition', 'screen-blend', 'dip-to-black', 'whiteboard-marker-drawing', 'luma-wipe',
             'view-transition'),
    api=('videobuilder.capabilities.transitions.flash_cut.flash_cut',),
    demo=lambda: demo.two_scenes(flash_cut, start=1.1, length=0.6),
)

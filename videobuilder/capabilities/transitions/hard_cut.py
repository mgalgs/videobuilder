"""Hard cut: the outgoing scene is replaced by the incoming one between one
frame and the next, with nothing drawn in between."""
from .. import _demo as demo
from ..schema import Technique


def hard_cut(cv, a, b, p, at=0.5):
    """Draw the cut at progress `p` (0 -> 1): `a(cv)` until `p` reaches `at`,
    then `b(cv)`. No frame ever shows both scenes.

    A film usually needs no overlap for a cut at all (a timeline cut of
    `'cut'` already does this between clips); this function is for when a
    cut sits inside the same `transition(cv, a, b, p)` slot as the others,
    e.g. so a sequence can swap a dissolve for a cut without restructuring."""
    (a if p < at else b)(cv)


TECHNIQUE = Technique(
    id='hard-cut',
    name='Hard cut',
    family='transitions',
    group='Cuts',
    aliases=('straight cut', 'cut'),
    definition='One frame shows the first scene and the very next frame shows the second, '
               'with no fade, motion or blend joining them.',
    phrasings=('just cut straight to the next shot',
               'switch scenes instantly, no transition',
               'jump from one scene to the other on a single frame'),
    related=('zoom-blur', 'gaussian-blur', 'film-edge-frame', 'push-in', 'cut-out-paper-animation',
             'whip-pan'),
    api=('videobuilder.techniques.transitions.hard_cut.hard_cut',),
    demo=lambda: demo.two_scenes(hard_cut),
)

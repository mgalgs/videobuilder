"""Cross Dissolve: the incoming scene fades up over the outgoing one, so for
a moment both are on screen at once, half and half, with no dip in between."""
from .. import _demo as demo
from ..schema import Technique


def cross_dissolve(cv, a, b, p, ease=None):
    """Draw the dissolve at progress `p` (0 -> 1): `a(cv)` underneath, `b(cv)`
    composited over it at opacity `p` (or `ease(p)`, for a curve other than
    the usual straight blend).

    In a film, call it while two shots are live in an overlap, e.g.
    `cross_dissolve(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    t = ease(p) if ease else p
    a(cv)
    with cv.layer(opacity=t):
        b(cv)


TECHNIQUE = Technique(
    id='cross-dissolve',
    name='Cross dissolve',
    family='transitions',
    group='Dissolves',
    aliases=('dissolve', 'crossfade', 'cross-fade', 'mix'),
    definition='One scene melts into the next: the new picture grows steadily more opaque on top '
               'of the old one until the old one is gone.',
    phrasings=('blend smoothly from this shot into the next one',
               'fade the two scenes into each other',
               'a soft overlap between the clips instead of a hard cut'),
    related=('cross-zoom', 'image-crossfade-slideshow', 'theme-swap-crossfade', 'lyric-line-crossfade',
             'cross-processing', 'typeface-crossfade'),
    api=('videobuilder.techniques.transitions.cross_dissolve.cross_dissolve',),
    demo=lambda: demo.two_scenes(cross_dissolve),
)

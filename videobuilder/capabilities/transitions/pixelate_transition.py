"""Pixelate Transition: the outgoing scene breaks up into ever-larger square
blocks, swaps for the incoming scene at its coarsest, and the incoming scene
sharpens back down from those blocks to full detail."""
from .. import _demo as demo
from ..schema import Technique


def pixelate_transition(cv, a, b, p, block=72, blend=0.12):
    """Draw the pixelate at progress `p` (0 -> 1): `a(cv)` coarsening from
    full detail to `block`-px squares by the middle, then `b(cv)` resolving
    back from `block`-px squares to full detail. Block size grows
    geometrically and steps in whole pixels, so each step reads as a jump in
    coarseness. For the `blend` fraction around the middle the two blocky
    scenes cross-fade, so the swap happens inside the mosaic, not as a cut.

    Uses `Canvas.pixelated`. In a film, call it while two shots are live in
    an overlap, e.g. `pixelate_transition(cv, lambda c: scene_a(c, old),
    lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = min(1.0, max(0.0, p))
    size = lambda d: max(1, round(block ** d))  # noqa: E731 -- d: 0 sharp -> 1 coarsest

    def draw(scene, d, alpha=1.0):
        s = size(d)
        with cv.layer(opacity=alpha):
            if s <= 1:
                scene(cv)
            else:
                with cv.pixelated(s) as sub:
                    scene(sub)

    lo, hi = 0.5 - blend / 2, 0.5 + blend / 2
    if p < lo:
        draw(a, p / lo)
    elif p > hi:
        draw(b, (1 - p) / (1 - hi))
    else:
        draw(a, 1.0)
        draw(b, 1.0, alpha=(p - lo) / (hi - lo))


TECHNIQUE = Technique(
    id='pixelate-transition',
    name='Pixelate transition',
    family='transitions',
    group='Pixel and Mosaic',
    aliases=('pixel transition', 'mosaic transition', 'pixelize', 'pixel dissolve'),
    definition='The first shot dissolves into chunkier and chunkier square pixels, then the next shot '
               'comes out of that blocky mosaic and sharpens back to full detail.',
    phrasings=('pixelate out of this shot and into the next one',
               'turn the picture into big blocky pixels and resolve it into the new scene',
               'a retro mosaic transition between the two clips'),
    related=('pixelation', 'pixelation-reveal', 'pixel-sorting', 'pixel-build', 'glitch-transition', 'liquify'),
    api=('videobuilder.techniques.transitions.pixelate_transition.pixelate_transition',
         'videobuilder.Canvas.pixelated'),
    demo=lambda: demo.two_scenes(pixelate_transition, start=0.7, length=1.6),
)

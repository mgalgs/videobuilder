"""Pixelate Transition: the same block mosaic as Pixelation (`../vfx/
pixelation.py`, itself merged into 8-bit pixel filter), used as a
transition instead of a filter: the outgoing scene breaks up into
ever-larger square blocks, swaps for the incoming scene at its coarsest,
and the incoming scene sharpens back down from those blocks to full
detail. This module's own code stays (a film may still import it), but it
is no longer a capability of its own."""
MERGED_INTO = 'pixelation'


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

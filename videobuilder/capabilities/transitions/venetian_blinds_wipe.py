"""Venetian blinds wipe: the frame is cut into even strips, and a sliver of
the incoming scene opens in the middle of each one, all together, until the
strips meet and the new scene fills the frame."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def venetian_blinds_wipe(cv, a, b, p, slats=10, vertical=False, stagger=0.0, ease=vb.ease_in_out_quart):
    """Draw the blinds at progress `p` (0 -> 1): `a(cv)` underneath, and
    `b(cv)` showing through `slats` bands that each grow out from their own
    centre line until they close up. Bands run across the frame (horizontal
    slats) unless `vertical`. `stagger` (0 -> under 1) delays each band after
    the one above it (or to its left) by that share of the move, so the
    blinds ripple open instead of opening as one.

    In a film, call it while two shots are live in an overlap, e.g.
    `venetian_blinds_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    a(cv)
    span = cv.height if not vertical else cv.width
    step = span / slats
    move = 1 - stagger
    c = cv.ctx
    c.save()
    c.new_path()
    for i in range(slats):
        delay = stagger * i / max(1, slats - 1)
        q = ease(vb.clamp01((p - delay) / move)) if move > 0 else float(p >= delay)
        if q <= 0:
            continue
        size = step * q
        # Pad by half a pixel each side so neighbours overlap as they close,
        # leaving no hairline of `a` between them.
        lo, hi = i * step + (step - size) / 2 - 0.5, size + 1
        if not vertical:
            c.rectangle(0, lo, cv.width, hi)
        else:
            c.rectangle(lo, 0, hi, cv.height)
    # One clip for every band, and `b` drawn once through it: clipping each
    # band on its own redraws `b` over the shared edge pixels, which darkens
    # them wherever `b` stacks a translucent layer (a shadow) under its fill.
    c.clip()
    try:
        b(cv)
    finally:
        c.restore()

CAPABILITY = Capability(
    id='venetian-blinds-wipe',
    name='Venetian blinds wipe',
    family='transitions',
    group='Wipes',
    aliases=('blinds wipe', 'slat wipe', 'blinds transition', 'shutter transition'),
    definition='The screen splits into a stack of thin bands, and every band opens out from its middle '
               'at once to show the next scene, like turning the slats of a window blind.',
    phrasings=('open the next shot like window blinds',
               'reveal the new scene through stripes that widen until they join',
               'a blinds-style wipe between the two scenes'),
    related=('shutter-slat-reveal', 'paint-brush-wipe', 'wipe-reveal', 'ribbon-sweep',
             'tile-grid-title-reveal', 'curtain-reveal'),
    api=('videobuilder.capabilities.transitions.venetian_blinds_wipe.venetian_blinds_wipe',),
    demo=lambda: demo.two_scenes(venetian_blinds_wipe, start=1.3, length=1.5),
)

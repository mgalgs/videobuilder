"""Blur dissolve: the outgoing scene goes soft, cross-fades into the incoming
scene while both are out of focus, and the incoming scene sharpens up."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type.kit import blurred


def _soft(cv, scene, radius, alpha):
    """`scene(cv)` blurred by `radius` at `alpha`. A slightly enlarged copy is
    drawn underneath so the blur pulls in picture, not empty space, at the
    frame's edges."""
    box = vb.Box.of(cv)
    pad = radius * 2.5
    grow = 1 + 2 * pad / min(box.w, box.h)

    def paint(c):
        with c.layer(dx=box.cx * (1 - grow), dy=box.cy * (1 - grow), scale=grow):
            scene(c)
        with c.clip(box.x, box.y, box.w, box.h):
            scene(c)
    with cv.clip(box.x, box.y, box.w, box.h):
        blurred(cv, box, radius, paint, alpha=alpha)


def blur_dissolve(cv, a, b, p, radius=48):
    """Draw the dissolve at progress `p` (0 -> 1): `a(cv)` blurs up towards
    `radius` px, cross-fades into `b(cv)` at the blurriest point, and `b`
    comes back into focus. The blur peaks at mid-way.

    In a film, call it while two shots are live in an overlap, e.g.
    `blur_dissolve(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    r = radius * math.sin(math.pi * vb.clamp01(p))
    mix = vb.clamp01((p - 0.25) / 0.5)
    mix = mix * mix * (3 - 2 * mix)
    _soft(cv, a, r, 1.0)
    if mix > 0:
        _soft(cv, b, r, mix)


CAPABILITY = Capability(
    id='blur-dissolve',
    name='Blur dissolve',
    family='transitions',
    group='Dissolves',
    aliases=('blur transition', 'defocus dissolve', 'blur cross-fade'),
    definition='The first shot drifts out of focus, melts into the next shot while both are soft, '
               'and the new shot then sharpens back to crisp.',
    phrasings=('blur the first scene out and bring the next one into focus',
               'a soft, dreamy cross-fade where everything goes blurry in the middle',
               'defocus into the next shot'),
    related=('gaussian-blur', 'noise-dissolve', 'zoom-blur', 'blur-up-image-load', 'spin-blur',
             'character-blur-in'),
    api=('videobuilder.capabilities.transitions.blur_dissolve.blur_dissolve', 'videobuilder.type.kit.blurred'),
    demo=lambda: demo.two_scenes(blur_dissolve, start=0.7, length=1.6),
)

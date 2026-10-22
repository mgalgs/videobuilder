"""Object pass-through: the camera trucks sideways past something close to
the lens -- a pillar, a tree trunk, a passer-by -- that sweeps across and
fills the whole frame for an instant, and the cut to the next scene is
hidden behind it."""
import math

from .. import _demo as demo
from ..schema import Capability


def pillar(cv, x, w, color='#15171c', light='#4a4f5a'):
    """The default foreground object: a dark round column spanning the frame
    height from `x` to `x + w`, shaded like a cylinder lit from the left."""
    cv.rect(x, 0, w, cv.height, color)
    bands = 48
    for i in range(bands):
        u = (i + 0.5) / bands
        shade = max(0.0, math.cos((u - 0.3) * math.pi)) ** 3  # brightest a third of the way across
        cv.rect(x + w * i / bands, 0, w / bands + 1, cv.height, light, alpha=0.55 * shade)
    cv.rect(x, 0, w * 0.015, cv.height, light, alpha=0.8)  # rim catching the light


def object_pass_through(cv, a, b, p, draw_object=pillar, width=1.2, drift=0.12, direction=-1):
    """Draw the pass-through at progress `p` (0 -> 1): a near object
    `draw_object(cv, x, w)`, `width` frames wide, crosses the frame at full
    speed while both scenes drift `drift` of a frame the same way, slower
    (parallax); `a(cv)` shows until the object covers the frame, `b(cv)`
    after. `direction` -1 moves things right to left, +1 left to right.

    In a film, call it while two shots are live in an overlap, e.g.
    `object_pass_through(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    ow = W * width
    travel = W + ow
    left = W - travel * p  # the object's left edge, for right-to-left motion
    cut = p >= 0.5          # the object fully covers the frame around p = 0.5
    # Scenes drift slower than the object, zoomed just enough that their edges never show
    # (back to 1 at p = 0 and 1, so the held shots either side match).
    shift = (-drift * W * 2 * p) if not cut else (drift * W * 2 * (1 - p))
    k = 1 + 2 * abs(shift) / W
    if direction > 0:
        shift, left = -shift, W - left - ow
    with cv.layer(dx=-(k - 1) * W / 2 + shift, dy=-(k - 1) * H / 2, scale=k):
        (b if cut else a)(cv)
    draw_object(cv, left, ow)


CAPABILITY = Capability(
    id='object-pass-through',
    name='Object pass-through',
    family='transitions',
    group='Cuts',
    aliases=('foreground wipe', 'wipe by object', 'hidden cut', 'pass-by wipe', 'natural wipe'),
    definition='The camera slides past something close to the lens that blots out the whole frame '
               'for a moment, and when it clears the shot has become the next scene.',
    phrasings=('hide the cut behind a pillar the camera moves past',
               'something big swipes across the lens and we come out in a new place',
               'use a foreground object to wipe from one shot to the next'),
    related=('zoom-through', 'fly-through', 'tracking-shot', 'follow-through', 'image-hover-mask-reveal',
             'uncover'),
    api=('videobuilder.capabilities.transitions.object_pass_through.object_pass_through',
         'videobuilder.capabilities.transitions.object_pass_through.pillar'),
    demo=lambda: demo.two_scenes(object_pass_through, start=0.7, length=1.6),
)

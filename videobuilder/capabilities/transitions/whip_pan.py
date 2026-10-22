"""Whip pan: the camera flicks sideways so fast the picture streaks into a
blur, and the next scene comes out of the streak from the other side."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

WHIP = vb.bezier(0.7, 0.0, 0.3, 1.0)   # slow off the mark, a violent middle, a quick settle
DIRECTIONS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}


def whip_pan(cv, a, b, p, direction='left', smear=0.35, samples=24, ease=WHIP):
    """Draw the whip at progress `p` (0 -> 1): `a(cv)` and `b(cv)` side by
    side on one strip, panned by `ease(p)` of a frame in `direction` (the way
    the picture moves; `b` enters from the opposite edge). The picture is
    box-blurred along the move in step with its speed: `smear` of the frame
    long at the middle of the whip, sharp at either end. `samples` copies
    build the blur.

    In a film, call it while two shots are live in an overlap, e.g.
    `whip_pan(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`;
    a whip of 8 to 18 frames reads as one flick."""
    dx, dy = DIRECTIONS[direction]
    span = cv.width if dx else cv.height
    p = vb.clamp01(p)
    pos = ease(p)

    def speed(t, h=1e-3):
        return (ease(min(1.0, t + h)) - ease(max(0.0, t - h))) / (min(1.0, t + h) - max(0.0, t - h))

    blur = smear * span * min(1.0, speed(p) / speed(0.5))
    n = max(2, round(samples * min(1.0, blur / (0.08 * span)))) if blur > 2 else 1

    def strip(off):
        o = pos * span - off
        for scene, at in ((a, o), (b, o - span)):
            # Each scene clipped to its own frame on the strip, so a full-frame fill stays on its side.
            with cv.layer(dx=dx * at, dy=dy * at), cv.clip(0, 0, cv.width, cv.height):
                scene(cv)

    with cv.clip(0, 0, cv.width, cv.height):
        strip(0 if n == 1 else -blur / 2)
        # Painting copy i at 1/(i+1) over the running result keeps every copy at equal weight: a box blur.
        for i in range(1, n):
            with cv.layer(opacity=1 / (i + 1)):
                strip(-blur / 2 + blur * i / (n - 1))


CAPABILITY = Capability(
    id='whip-pan',
    name='Whip pan',
    family='transitions',
    group='Motion Blur',
    aliases=('whip transition', 'swish pan', 'flick pan', 'directional blur swipe'),
    definition='The view jerks sideways so quickly that everything streaks into a horizontal blur, '
               'and the new scene slides out of that streak and snaps sharp.',
    phrasings=('whip the camera across to the next shot',
               'a fast blurry swish from one scene to the other',
               'flick sideways with motion blur into the next part'),
    related=('pan', 'ken-burns-effect', 'motion-blur', 'smear-frame', 'zoom-blur', 'morph-cut'),
    api=('videobuilder.capabilities.transitions.whip_pan.whip_pan', 'videobuilder.bezier'),
    demo=lambda: demo.two_scenes(whip_pan, start=1.0, length=0.6),
)

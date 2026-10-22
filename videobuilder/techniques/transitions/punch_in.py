"""Punch-in: the outgoing shot jumps in toward a point, smeared by a zoom
blur, and the cut to the incoming shot lands inside the jump, which settles
from a little too close."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def zoomed(cv, draw, scale, cx=None, cy=None, blur_from=None, steps=6):
    """`draw(cv)` scaled by `scale` about (cx, cy) (default the frame centre).
    With `blur_from`, the copies between that scale and `scale` are averaged,
    a zoom blur for a frame that moves fast."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    scales = [scale] if blur_from is None or abs(blur_from - scale) < 1e-3 else \
        [vb.log_lerp(blur_from, scale, i / (steps - 1)) for i in range(steps)]
    for k, s in enumerate(scales):
        with cv.layer(opacity=1 / (k + 1), dx=cx * (1 - s), dy=cy * (1 - s), scale=s):  # running mean
            draw(cv)


def punch_in(cv, a, b, p, amount=2.6, settle=1.2, cut=0.5, cx=None, cy=None, blur=True):
    """Draw the punch-in at progress `p` (0 -> 1). Until `cut`, `a(cv)` zooms
    from 1 to `amount` about (cx, cy), accelerating; then `b(cv)` arrives at
    `settle` and eases back to 1. `blur` smears the fastest frames.

    In a film, call it over a short overlap (a third to half a second reads
    as a punch), e.g. `punch_in(cv, lambda c: wide(c, n), lambda c: close(c, n), f / overlap_frames)`."""
    if p < cut:
        q = p / cut
        s = vb.log_lerp(1.0, amount, q * q)
        prev = vb.log_lerp(1.0, amount, max(0.0, q - 0.12) ** 2)
        zoomed(cv, a, s, cx, cy, blur_from=prev if blur else None)
    else:
        q = (p - cut) / (1 - cut)
        s = vb.log_lerp(settle, 1.0, 1 - (1 - q) ** 3)
        prev = vb.log_lerp(settle, 1.0, 1 - (1 - max(0.0, q - 0.12)) ** 3) if q < 0.5 else None
        zoomed(cv, b, s, cx, cy, blur_from=prev if blur else None)


def _wide(cv):
    """A wide shot: a dot sitting on a ground line, small in the frame."""
    cv.fill(demo.BG)
    demo.floor(cv, demo.H / 2 + 40)
    demo.dot(cv, demo.W / 2, demo.H / 2, r=40)
    demo.word(cv, 'WIDE', demo.W / 2, demo.H / 2 + 110, size=44, color=demo.MUTED)


def _close(cv):
    """The close-up: the same dot filling the frame."""
    cv.fill(demo.BG)
    demo.floor(cv, demo.H * 0.9, color=demo.LINE)
    demo.dot(cv, demo.W / 2, demo.H / 2, r=300)
    demo.word(cv, 'CLOSE', demo.W / 2, demo.H / 2, size=120, color=demo.BG)


TECHNIQUE = Technique(
    id='punch-in',
    name='Punch-in',
    family='transitions',
    group='Zoom',
    aliases=('snap zoom', 'punch zoom', 'crash zoom', 'whip zoom', 'zoom punch', 'smash zoom'),
    definition='The frame lunges in toward the subject in a fraction of a second, blurred by its own speed, '
               'and lands on a tighter shot or the next cut.',
    phrasings=('snap in tight on the subject',
               'a fast zoom right into it on the beat',
               'jump from the wide shot straight into a close-up with a quick zoom'),
    related=('scale-zoom-through', 'smash-cut', 'ui-walkthrough-camera-zoom', 'image-hover-zoom',
             'impact-shake', 'impact-hit'),
    api=('videobuilder.techniques.transitions.punch_in.punch_in',
         'videobuilder.techniques.transitions.punch_in.zoomed'),
    demo=lambda: demo.two_scenes(punch_in, start=1.0, length=0.8, a=_wide, b=_close),
)

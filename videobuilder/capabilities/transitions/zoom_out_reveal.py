"""Zoom out reveal: the outgoing scene pulls back into a small framed
picture, and the incoming scene turns out to be the backdrop it sat on."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def zoom_out_reveal(cv, a, b, p, size=0.3, anchor=(0.5, 0.5), shrink=0.75, radius=24, border='#ffffff'):
    """Draw the pull-back at progress `p` (0 -> 1): `b(cv)` fills the frame
    while `a(cv)` shrinks, whole, into a framed inset `size` times the frame,
    closing on `anchor` (a point as fractions of the frame). The shrink takes
    the first `shrink` of `p`; the inset then fades away over the rest, leaving `b`.

    In a film, call it while two shots are live in an overlap, e.g.
    `zoom_out_reveal(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`.
    For a pull-out that keeps the inset, pass `shrink=1` and hold the last frame."""
    w, h = cv.width, cv.height
    t = vb.ease_in_out_quart(vb.clamp01(p / shrink)) if shrink > 0 else 1.0
    fade = 1.0 if shrink >= 1 else 1 - vb.clamp01((p - shrink) / (1 - shrink))
    s = 1 + (size - 1) * t
    ax, ay = anchor[0] * w, anchor[1] * h
    x, y = ax * (1 - s), ay * (1 - s)
    r = radius * t
    b(cv)
    if fade <= 0:
        return
    with cv.layer(opacity=fade):
        cv.shadow(x, y, w * s, h * s, radius=r, dy=18 * t, blur=48 * t, color=(0, 0, 0, 0.5 * t))
        with cv.clip(x, y, w * s, h * s, radius=r):
            with cv.layer(dx=x, dy=y, scale=s):
                a(cv)
        if t > 0:
            cv.outline(x, y, w * s, h * s, border, width=6 * t, radius=r, alpha=t)


CAPABILITY = Capability(
    id='zoom-out-reveal',
    name='Zoom out reveal',
    family='transitions',
    group='Zoom',
    aliases=('pull-out', 'pull back reveal', 'pull-out reveal', 'wide reveal'),
    definition='The current shot backs away from the viewer until it is just a small framed picture, '
               'and the next scene appears as the larger world around it.',
    phrasings=('pull back from the first shot so it becomes a little picture on the next scene',
               'zoom the video out into a small box to show the new background behind it',
               'make the clip shrink away and reveal what it was sitting on'),
    related=('uncover', 'roll-up', 'corner-wipe', 'scroll-linked-clip-reveal', 'fade-up-scroll-reveal', 'push'),
    api=('videobuilder.capabilities.transitions.zoom_out_reveal.zoom_out_reveal',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: zoom_out_reveal(cv, a, b, p, size=0.25, anchor=(0.96, 0.94)),
                                 start=0.5, length=2.0),
)

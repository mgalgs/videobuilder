"""Zoom blur: the outgoing scene rushes toward the viewer, smearing into
streaks that fly out from the centre; under the heaviest smear it becomes the
incoming scene, which settles back into focus as the streaks die away."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def radial_blur(cv, draw, zoom=1.0, amount=0.3, samples=24, cx=None, cy=None):
    """Draw `draw(cv)` scaled by `zoom` about (cx, cy) (default the frame's
    centre) with a radial zoom blur: copies of it, each a little larger, out
    to `1 + amount` times, averaged evenly. `amount` 0 draws it sharp."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    c = cv.ctx
    c.push_group()
    c.save()
    c.translate(cx, cy)
    c.scale(zoom, zoom)
    c.translate(-cx, -cy)
    draw(cv)
    c.restore()
    pattern = c.pop_group()
    pattern.set_matrix(cairo.Matrix())  # pattern space = device space, as the group was drawn
    n = max(1, int(samples)) if amount > 0 else 1
    dx, dy = cx * cv.scale, cy * cv.scale  # the copies scale in device space, where the group lives
    for i in range(n):
        k = 1 + amount * (i / (n - 1) if n > 1 else 0)
        c.save()
        c.identity_matrix()
        c.translate(dx, dy)
        c.scale(k, k)
        c.translate(-dx, -dy)
        c.set_source(pattern)
        c.paint_with_alpha(1 / (i + 1))  # a running average: every copy weighs the same
        c.restore()


def zoom_blur(cv, a, b, p, zoom=2.2, blur=0.45, cut=0.5, mix=0.12, samples=24):
    """Draw the zoom blur at progress `p` (0 -> 1): `a(cv)` pushes in toward
    `zoom` times its size while a radial blur builds to `blur`, then around
    `cut` (cross-mixed over `mix` either side) `b(cv)` takes over, already
    pushed in and blurred, and eases back to sharp at full size.

    In a film, call it while two shots are live in an overlap, e.g.
    `zoom_blur(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    qa = min(p, cut) / cut                 # a's push-in, 0 -> 1, held at 1 past the cut
    qb = max(0.0, p - cut) / (1 - cut)     # b's pull-back, 0 until the cut, then 0 -> 1
    w = vb.clamp01((p - (cut - mix)) / (2 * mix)) if mix > 0 else float(p >= cut)
    if w < 1:
        radial_blur(cv, a, vb.log_lerp(1, zoom, qa ** 2), blur * math.sin(qa * math.pi / 2) ** 2, samples)
    if w > 0:
        with cv.layer(opacity=w):
            radial_blur(cv, b, vb.log_lerp(zoom, 1, 1 - (1 - qb) ** 2), blur * math.cos(qb * math.pi / 2) ** 2,
                        samples)


CAPABILITY = Capability(
    id='zoom-blur',
    name='Zoom blur',
    family='transitions',
    group='Zoom',
    aliases=('radial zoom blur', 'speed zoom', 'zoom streak', 'push blur', 'zoom burst'),
    definition='The first shot lunges toward the camera and smears into streaks radiating from the centre, '
               'and the next shot pulls out of that smear back into sharp focus.',
    phrasings=('zoom into the shot with a motion blur and land on the next one',
               'a fast blurry punch-in that cuts to the next scene',
               'whoosh into the middle of the frame and come out on the new clip'),
    related=('spin-blur', 'gaussian-blur', 'motion-blur', 'gooey-filter', 'tilt-shift-miniature',
             'blur-up-image-load'),
    api=('videobuilder.capabilities.transitions.zoom_blur.zoom_blur',
         'videobuilder.capabilities.transitions.zoom_blur.radial_blur'),
    demo=lambda: demo.two_scenes(zoom_blur, start=1.3, length=1.2),
)

"""Zoom through: the camera punches into the outgoing scene, which swells
past the lens faster and faster, smeared by a trail of fading copies (a zoom
blur drawn in code), and the incoming scene arrives out of the rush from
slightly small, settling to full frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

RUSH = vb.bezier(0.45, 0.0, 0.9, 0.7)   # accelerating into the lens


def _scaled(cv, s, opacity=1.0):
    """A layer scaled by `s` about the frame's centre."""
    cx, cy = cv.width / 2, cv.height / 2
    return cv.layer(opacity=opacity, dx=cx - cx * s, dy=cy - cy * s, scale=s)


def zoom_through(cv, a, b, p, zoom=9.0, out_end=0.7, in_start=0.45, start_scale=0.8, echoes=5,
                 background='#000000'):
    """Draw the zoom through at progress `p` (0 -> 1).

    `a(cv)` scales from 1 up to `zoom` about the centre on an accelerating
    curve, trailed by `echoes` fainter, smaller copies, and fades as it
    passes the lens by `out_end` of the way. Behind it `b(cv)` fades in from
    `in_start`, growing from `start_scale` to full frame on `background`.

    In a film, call it while two shots are live in an overlap, e.g.
    `zoom_through(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    cv.fill(background)
    t = vb.clamp01((p - in_start) / (1 - in_start))
    if t > 0:
        s = start_scale + (1 - start_scale) * vb.ease_out_quint(t)
        with _scaled(cv, s, opacity=vb.clamp01(t * 4)):
            with cv.clip(0, 0, cv.width, cv.height):
                b(cv)
    q = vb.clamp01(p / out_end)
    if q >= 1:
        return
    k = RUSH(q)
    z = math.exp(math.log(zoom) * k)
    speed = vb.clamp01(math.log(zoom) * (RUSH(min(1.0, q + 0.04)) - k) / 0.04 / 6)   # how fast the zoom moves
    fade = 1 - vb.clamp01((q - 0.6) / 0.4)
    for e in range(echoes, 0, -1):
        zs = z * math.exp(-0.21 * e * speed)
        with _scaled(cv, zs, opacity=fade * 0.32 * speed * (1 - e / (echoes + 1))):
            a(cv)
    with _scaled(cv, z, opacity=fade):
        a(cv)


TECHNIQUE = Technique(
    id='zoom-through',
    name='Zoom through',
    family='transitions',
    group='Zoom',
    aliases=('zoom transition', 'punch-through zoom', 'zoom-in transition', 'lens punch'),
    definition='The camera rushes into the first scene until it blows past the lens in a blur, '
               'and the next scene comes up out of that rush and settles into place.',
    phrasings=('zoom right into the first shot and come out on the next one',
               'punch through the screen into the next scene',
               'a fast zoom-in that carries us to the next shot'),
    related=('push-in', 'scale-zoom-through', 'ui-walkthrough-camera-zoom', 'fly-through', 'infinite-zoom-tunnel',
             'object-pass-through'),
    api=('videobuilder.techniques.transitions.zoom_through.zoom_through',
         'videobuilder.compendium.components.transition_zoom_through.COMPONENT'),
    demo=lambda: demo.two_scenes(zoom_through, start=0.7, length=1.6),
)

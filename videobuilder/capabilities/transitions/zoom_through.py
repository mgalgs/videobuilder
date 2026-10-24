"""Zoom Through: the same rush as Cross Zoom (`cross_zoom.py`, which keeps
the capability) -- the camera punches into the outgoing scene, smeared by a
trail of fading copies, and swaps at the peak for the incoming scene, which
settles out of the rush into full frame. This module's own code stays (a
film may still import it), but it is no longer a capability of its own."""
import math

import videobuilder as vb

MERGED_INTO = 'cross-zoom'

RUSH = vb.bezier(0.45, 0.0, 0.9, 0.7)   # accelerating into the lens


def _scaled(cv, s, opacity=1.0):
    """A layer scaled by `s` about the frame's centre."""
    cx, cy = cv.width / 2, cv.height / 2
    return cv.layer(opacity=opacity, dx=cx - cx * s, dy=cy - cy * s, scale=s)


def zoom_through(cv, a, b, p, zoom=9.0, out_end=0.75, in_start=0.4, start_scale=0.6, echoes=5,
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
        with _scaled(cv, s, opacity=vb.clamp01(t * 3)):
            with cv.clip(0, 0, cv.width, cv.height):
                b(cv)
    q = vb.clamp01(p / out_end)
    if q >= 1:
        return
    k = RUSH(q)
    z = math.exp(math.log(zoom) * k)
    speed = vb.clamp01(math.log(zoom) * (RUSH(min(1.0, q + 0.04)) - k) / 0.04 / 6)   # how fast the zoom moves
    fade = 1 - vb.clamp01((q - 0.65) / 0.35)
    with _scaled(cv, z, opacity=fade):
        a(cv)
    # the blur: lagging, smaller copies laid over the scene (under it, an
    # opaque full-frame scene would hide them), stronger the faster it zooms
    for e in range(1, echoes + 1):
        zs = z * math.exp(-0.3 * e * speed)
        with _scaled(cv, zs, opacity=fade * 0.5 * speed * (1 - e / (echoes + 1))):
            a(cv)

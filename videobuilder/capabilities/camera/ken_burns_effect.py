"""Ken Burns effect: a still picture fills the frame and the camera drifts
across it, slowly pushing in (or pulling out) while it pans, so a photo
plays like a shot."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _slow_both_ends(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ken_burns_view(img, box, p, start=(0.4, 0.55, 1.0), end=(0.62, 0.42, 1.35), ease=None):
    """(center, scale) for `cv.view` at progress `p` (0 -> 1) of a Ken Burns
    move on `img` seen through `box`. `start` and `end` are framings
    (fx, fy, zoom): the image point (fx, fy) in 0-1 fractions at the box's
    centre, at `zoom` times the cover scale. Zoom moves geometrically and the
    centre is kept where the picture still covers the box. `ease` shapes `p`
    (default a sine ease, slow at both ends)."""
    box = vb.Box(*box)
    q = (ease or _slow_both_ends)(vb.clamp01(p))
    (fx0, fy0, z0), (fx1, fy1, z1) = start, end
    s = max(box.w / img.w, box.h / img.h) * vb.log_lerp(z0, z1, q)
    half_w, half_h = box.w / s / 2, box.h / s / 2
    cx = min(img.w - half_w, max(half_w, img.w * (fx0 + (fx1 - fx0) * q)))
    cy = min(img.h - half_h, max(half_h, img.h * (fy0 + (fy1 - fy0) * q)))
    return (cx, cy), s


def ken_burns(cv, img, p, box=None, start=(0.4, 0.55, 1.0), end=(0.62, 0.42, 1.35), ease=None, radius=0):
    """Draw `img` in `box` (default the whole frame) at progress `p` of a
    slow pan and zoom from framing `start` to framing `end` (see
    `ken_burns_view`). Returns the `View`, so overlays can `pin` to the picture.

    In a film, run `p` across the whole shot, e.g. `ken_burns(cv, photo, shot.f / shot.length)`;
    swap `start` and `end` to pull out instead of pushing in."""
    box = vb.Box.of(cv) if box is None else vb.Box(*box)
    center, scale = ken_burns_view(img, box, p, start, end, ease)
    return cv.view(img, box, center=center, scale=scale, radius=radius)


START, END = (0.32, 0.6, 1.0), (0.66, 0.4, 1.45)


def draw(n, cv):
    img = demo.photo()
    p = demo.phase(n, 0.0, demo.SECONDS)
    ken_burns(cv, img, p, start=START, end=END)
    # A small map of the whole photo, with the part on screen outlined.
    tw = 260
    th = tw * img.h / img.w
    tx, ty = demo.W - tw - 36, demo.H - th - 36
    cv.shadow(tx, ty, tw, th, radius=8, dy=6, blur=18, color=(0, 0, 0, 0.5))
    cv.view(img, (tx, ty, tw, th), radius=8)
    cv.outline(tx, ty, tw, th, demo.INK, width=2, radius=8, alpha=0.6)
    (cx, cy), s = ken_burns_view(img, vb.Box.of(cv), p, START, END)
    k = tw / img.w
    vw, vh = demo.W / s * k, demo.H / s * k
    cv.outline(tx + cx * k - vw / 2, ty + cy * k - vh / 2, vw, vh, demo.ACCENT, width=3)


CAPABILITY = Capability(
    id='ken-burns-effect',
    name='Ken Burns effect',
    family='camera',
    group='Camera moves',
    aliases=('pan and zoom', 'photo pan-zoom', 'slow zoom', 'slow pan', 'Ken Burns pan and zoom'),
    definition='A still picture fills the screen while the view creeps across it and gently pushes in, '
               'so a photo moves like footage.',
    phrasings=('make the photo slowly drift and zoom in like in a history documentary',
               'give the still image some gentle camera movement',
               'slowly push into the picture while panning across it'),
    related=('whip-pan', 'canvas-pan-and-zoom', 'zoom-blur', 'tilt-shift-miniature', 'image-hover-zoom',
             'infinite-zoom-tunnel'),
    api=('videobuilder.capabilities.camera.ken_burns_effect.ken_burns',
         'videobuilder.capabilities.camera.ken_burns_effect.ken_burns_view',
         'videobuilder.Canvas.view'),
    demo=lambda: demo.film(draw),
)

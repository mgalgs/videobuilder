"""Vignette: the edges and corners of the picture fall off into shadow, the
way an old lens darkens away from its centre, so the eye settles on the middle."""
import cairo

import videobuilder as vb
from videobuilder import Box
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def vignette(cv, amount=0.6, inner=0.45, color='#000000', box=None, center=None, oval=True):
    """Darken `box` (default the whole frame) towards its edges: clear inside
    `inner` (0-1, a fraction of the centre-to-corner distance), easing to
    `color` at `amount` opacity in the corners. `center` (x, y) moves the
    bright spot; `oval` stretches the falloff to the box's shape (a lens
    look) instead of a circle. Draw it last, over the finished shot; animate
    `amount` or `inner` to make it close in or open up."""
    if amount <= 0:
        return
    box = Box(*box) if box is not None else Box.of(cv)
    cx, cy = center if center is not None else (box.cx, box.cy)
    r, g, b, a = rgba(color)
    inner = min(max(inner, 0.0), 0.99)
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(*box)
    ctx.clip()
    ctx.translate(cx, cy)
    # reach the farthest corner of the box from the centre
    rx, ry = max(cx - box.x, box.right - cx), max(cy - box.y, box.bottom - cy)
    if oval:
        ctx.scale(1.0, ry / rx)
        reach = rx * 2 ** 0.5
    else:
        reach = (rx * rx + ry * ry) ** 0.5
    grad = cairo.RadialGradient(0, 0, reach * inner, 0, 0, reach)
    steps = 8  # a smoothstep ramp, so the falloff has no visible ring
    for i in range(steps + 1):
        t = i / steps
        grad.add_color_stop_rgba(t, r, g, b, a * amount * t * t * (3 - 2 * t))
    ctx.set_source(grad)
    ctx.paint()
    ctx.restore()


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *Box.of(cv).cover(img.w, img.h))
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.0))
    vignette(cv, amount=0.92 * p, inner=0.7 - 0.45 * p)


CAPABILITY = Capability(
    id='vignette',
    name='Vignette',
    family='camera',
    group='Lens',
    aliases=('edge darkening', 'lens falloff', 'light falloff', 'vignetting'),
    definition='The corners and edges of the frame fade softly into shadow while the centre stays bright, '
               'drawing the eye inward.',
    phrasings=('darken the edges of the shot so the middle pops',
               'give it that moody dark-corners look',
               'add a soft shadow around the border of the picture'),
    related=('spotlight-dim', 'gradient-border-spin', 'solarization', 'lens-dirt-overlay',
             'tilt-shift-miniature', 'theme-swap-crossfade'),
    api=('videobuilder.capabilities.camera.vignette.vignette',),
    demo=lambda: demo.film(draw),
)

"""Gaussian blur: videobuilder already has it as `videobuilder.type.kit.blurred`
(anything a paint function draws, softened by a Gaussian of a given radius),
so this entry only names it and demos it: a photo going soft and coming back
into focus, with its blur radius read out underneath."""
import math

import videobuilder as vb
from videobuilder.type.kit import blurred

from .. import _demo as demo
from ..schema import Technique

PANEL = vb.Box(demo.W / 2 - 300, 50, 600, 338)
MAX_RADIUS = 18


def radius_at(n):
    """Blur radius at frame `n`: sharp, eased up to `MAX_RADIUS`, held, eased back to sharp."""
    up = vb.ease_in_out_quart(demo.phase(n, 0.35, 1.25))
    down = vb.ease_in_out_quart(demo.phase(n, 1.8, 2.7))
    return MAX_RADIUS * (up - down)


def draw(n, cv):
    r = radius_at(n)
    img = demo.photo()
    pad = r * 2.5

    def paint(c):  # the photo covers the panel grown by the blur, so its edges stay picture
        c.image(img, *vb.Box(PANEL.x - pad, PANEL.y - pad, PANEL.w + 2 * pad, PANEL.h + 2 * pad).cover(img.w, img.h))
    cv.shadow(PANEL.x, PANEL.y, PANEL.w, PANEL.h, radius=12, dy=8, blur=24, color=(0, 0, 0, 0.45))
    with cv.clip(PANEL.x, PANEL.y, PANEL.w, PANEL.h, radius=12):
        blurred(cv, PANEL, r, paint)

    # the readout: a track with a knob at the current radius, and the number
    x0, x1, y = PANEL.x + 90, PANEL.right - 110, PANEL.bottom + 62
    cv.line(x0, y, x1, y, demo.LINE, width=4)
    k = x0 + (x1 - x0) * r / MAX_RADIUS
    cv.line(x0, y, k, y, demo.ACCENT, width=4)
    demo.dot(cv, k, y, r=9)
    f = demo.mono(20, 600)
    vb.text.draw(cv, ['blur'], f, PANEL.x, y - 12, demo.MUTED)
    vb.text.draw(cv, [f'{math.floor(r + 0.5):>2d} px'], f, x1 + 28, y - 12, demo.INK)


TECHNIQUE = Technique(
    id='gaussian-blur',
    name='Gaussian blur',
    family='vfx',
    group='Blur & focus',
    aliases=('blur', 'soften', 'defocus', 'gaussian smoothing'),
    definition='Everything in the picture is softened evenly, each point smeared into a smooth haze '
               'around it, so detail and edges melt away as the blur radius grows.',
    phrasings=('make the background soft and out of focus',
               'blur the image so you can barely make out the details',
               'smoothly blur it up and then bring it back to sharp'),
    related=('blur-dissolve', 'blur-up-image-load', 'zoom-blur', 'nearest-neighbor-upscale', 'pixelation',
             'gradient-wipe'),
    api=('videobuilder.type.kit.blurred',),
    demo=lambda: demo.film(draw),
)

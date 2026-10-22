"""Desaturation: the colour drains out of the picture, leaving its light and
shade intact, until it is grey (or only faintly tinted)."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def desaturate(cv, amount):
    """Take `amount` (0 -> 1) of the colour out of everything already drawn
    inside the current clip: 0 leaves it alone, 1 leaves pure grey. Each
    pixel keeps its hue and brightness while its saturation drops, so the
    picture reads the same, only drained. Animate `amount` for a colour
    drain; hold it part-way for a muted grade."""
    amount = vb.clamp01(amount)
    if amount <= 0:
        return
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_HSL_SATURATION)
    c.set_source_rgb(0.5, 0.5, 0.5)  # any grey: only its (zero) saturation is used
    c.paint_with_alpha(amount)
    c.restore()


def desaturated(cv, scene, amount):
    """Draw `scene(cv)` with `amount` (0 -> 1) of its colour taken out,
    leaving whatever was under it untouched. In a film, e.g.
    `desaturated(cv, lambda c: shot(c, f), ease_in_out(f / frames))`."""
    c = cv.ctx
    c.push_group()
    scene(cv)
    desaturate(cv, amount)
    c.pop_group_to_source()
    c.paint()


def _draw(n, cv):
    p = demo.phase(n, 0.6, 2.4)
    p = p * p * (3 - 2 * p)
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    desaturate(cv, p)
    f = demo.mono(26)
    label = f'saturation {round(100 * (1 - p)):3d}%'
    w, h = vb.text.block_size([label], f)
    x, y = demo.W - w - 40, demo.H - h - 36
    cv.rect(x - 14, y - 8, w + 28, h + 16, demo.BG, radius=10, alpha=0.7)
    vb.text.draw(cv, [label], f, x, y, demo.INK)


CAPABILITY = Capability(
    id='desaturation',
    name='Desaturation',
    family='vfx',
    group='Color & grading',
    aliases=('grayscale fade', 'color drain', 'partial desaturation', 'fade to black and white'),
    definition='The colour slowly bleeds out of the picture while its shapes and shading stay put, '
               'until only greys (or a faint trace of colour) remain.',
    phrasings=('drain the colour out of the shot until it is black and white',
               'slowly turn the image grey',
               'mute the colours down to almost monochrome'),
    related=('dip-to-black', 'blur-up-image-load', 'pixelate-transition', 'gradient-wipe', 'gaussian-blur',
             'pixelation'),
    api=('videobuilder.capabilities.vfx.desaturation.desaturate',
         'videobuilder.capabilities.vfx.desaturation.desaturated'),
    demo=lambda: demo.film(_draw),
)

"""Difference blend: a top layer is composited by subtracting it from what is
under it and keeping the size of the result, so wherever the two match the
picture cancels to black and only the places they disagree light up."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def difference_blend(cv, base, top, amount=1.0, dx=0.0, dy=0.0):
    """Draw `base(cv)`, then `top(cv)` over it in difference mode: each pixel
    becomes |base - top| per channel, so equal areas go black, black in
    either layer leaves the other unchanged, and white inverts. `amount`
    (0 -> 1) is how strongly the top layer applies; `dx`, `dy` offset it,
    which is how a copy of the same picture turns into a glowing outline.

    In a film, call it with any two draw functions, e.g.
    `difference_blend(cv, lambda c: shot(c, n), lambda c: shot(c, n - 4))` to
    show only what moved between two frames."""
    base(cv)
    if amount <= 0:
        return
    c = cv.ctx
    c.save()
    c.push_group()
    c.translate(dx, dy)
    top(cv)
    c.pop_group_to_source()
    c.set_operator(cairo.OPERATOR_DIFFERENCE)
    c.paint_with_alpha(min(1.0, amount))
    c.restore()


PANEL = (demo.W / 2 - 300, demo.H / 2 - 180, 600, 340)


def _picture(cv):
    """The demo's subject: a framed photo with a dot and a word on it."""
    img = demo.photo()
    x, y, w, h = PANEL
    with cv.clip(x, y, w, h, 16):
        cv.image(img, *vb.Box(x, y, w, h).cover(img.w, img.h))
        demo.dot(cv, x + w * 0.74, y + h * 0.3, r=42, color=demo.ACCENT)
        demo.word(cv, 'SAME', x + w * 0.32, y + h * 0.66, size=96, color=demo.INK)


def _draw(n, cv):
    # A copy slides in from the right and lands on the original (everything
    # cancels to black), then drifts a few pixels so only the edges glow.
    slide = vb.ease_out_quint(demo.phase(n, 0.3, 1.6))
    drift = demo.phase(n, 2.0, 2.6)
    dx = (1 - slide) * (PANEL[2] + 60) + 12 * vb.ease_in_out_quart(drift)
    dy = -8 * vb.ease_in_out_quart(drift)
    difference_blend(cv, _picture, _picture, dx=dx, dy=dy)
    demo.word(cv, 'difference', demo.W / 2, demo.H - 30, size=22, color=demo.MUTED, weight=600)


TECHNIQUE = Technique(
    id='difference-blend',
    name='Difference blend',
    family='vfx',
    group='Blend & composite',
    aliases=('difference mode', 'subtract blend', 'inverted overlap'),
    definition='A layer is laid over another so that each pixel shows how far apart the two are, '
               'turning matching areas black and making only the mismatches shine.',
    phrasings=('put a copy on top so wherever they line up it goes black',
               'show only what is different between the two layers',
               'overlap two images so the matching parts cancel out and the edges glow'),
    related=('difference-highlight', 'additive-dissolve', 'cross-dissolve', 'theme-swap-crossfade',
             'pixelate-transition', 'palette-shift-transition'),
    api=('videobuilder.techniques.vfx.difference_blend.difference_blend',),
    demo=lambda: demo.film(_draw),
)

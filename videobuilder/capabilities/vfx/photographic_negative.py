"""Photographic negative: every colour in the picture flips to its opposite --
lights go dark, darks go light, blue sky turns amber -- like holding a strip
of developed film up to the light."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

FILM_BASE = '#e8a46a'  # the orange mask of colour negative film


def photographic_negative(cv, amount=1.0, x=0.0, y=0.0, w=None, h=None, film_base=None):
    """Invert what is already drawn on `cv` inside (x, y, w, h) (default the
    whole frame). `amount` 0 -> 1 blends from the untouched picture to the
    full negative. `film_base`, a colour such as `FILM_BASE`, multiplies the
    negative by that tint for the orange cast of colour negative film.

    Call it after drawing the shot, e.g. `scene(cv); photographic_negative(cv, p)`.
    The region must already be opaque (a background drawn under it)."""
    if amount <= 0:
        return
    w = cv.width - x if w is None else w
    h = cv.height - y if h is None else h
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    c.set_operator(cairo.OPERATOR_DIFFERENCE)  # |white - dst| = 1 - dst per channel
    c.set_source_rgb(1, 1, 1)
    c.paint_with_alpha(min(1.0, amount))
    if film_base:
        c.set_operator(cairo.OPERATOR_MULTIPLY)
        cv.fill(film_base, alpha=min(1.0, amount))
    c.restore()


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    # A seam sweeps left to right; behind it the picture is a negative.
    p = demo.phase(n, 0.6, 1.8)
    edge = demo.W * (p * p * (3 - 2 * p))
    photographic_negative(cv, w=edge)
    if 0 < p < 1:
        cv.line(edge, 0, edge, demo.H, demo.INK, width=4)
    f = demo.font(28, 800)
    if p > 0:
        demo.word(cv, 'NEGATIVE', 120, 50, size=28, color='#141414', font=f)
    if p < 1:
        demo.word(cv, 'POSITIVE', demo.W - 120, 50, size=28, color='#ffffff', font=f)


TECHNIQUE = Technique(
    id='photographic-negative',
    name='Photographic negative',
    family='vfx',
    group='Color & grading',
    aliases=('invert colors', 'color inversion', 'film negative', 'negative image'),
    definition='Every tone in the picture is flipped to its opposite, so bright areas go dark, '
               'dark areas go bright and each colour turns into its complement.',
    phrasings=('make the shot look like a film negative',
               'invert all the colours in the picture',
               'flip it to a negative for a moment'),
    related=('dip-to-black', 'vignette', 'night-vision', 'thermal-false-color', 'infrared-false-color', 'x-ray'),
    api=('videobuilder.techniques.vfx.photographic_negative.photographic_negative',),
    demo=lambda: demo.film(draw),
)

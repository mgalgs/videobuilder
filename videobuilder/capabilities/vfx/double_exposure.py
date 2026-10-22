"""Double Exposure: a second picture laid over the first as light, the way two
exposures on one frame of film stack up, so both stay readable at once -- the
bright parts of each show through the other instead of one covering it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

_BLENDS = {'screen': cairo.OPERATOR_SCREEN, 'add': cairo.OPERATOR_ADD, 'over': cairo.OPERATOR_OVER}


def double_exposure(cv, a, b, amount=0.6, blend='screen'):
    """Draw `a(cv)`, then superimpose `b(cv)` on it at strength `amount`
    (0 -> 1). `blend` is how the two combine: `'screen'` (the default, like
    film -- lights pile up, darks let the base through), `'add'` (hotter,
    clips sooner) or `'over'` (a plain see-through overlay).

    Unlike a dissolve this is a held look, not a change of shot: keep
    `amount` steady (or ease it up once) while both pictures play, e.g.
    `double_exposure(cv, lambda c: city(c, f), lambda c: portrait(c, f), 0.55)`."""
    a(cv)
    k = max(0.0, min(1.0, amount))
    if k <= 0:
        return
    c = cv.ctx
    c.save()
    c.push_group()
    b(cv)
    c.pop_group_to_source()
    c.set_operator(_BLENDS[blend])
    c.paint_with_alpha(k)
    c.restore()


def _landscape(cv):
    """The base exposure: the kit's photo, full frame."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def _portrait(cv, drift=0.0):
    """The second exposure: a pale head-and-shoulders silhouette on black,
    drifting slowly so it reads as its own layer."""
    W, H = demo.W, demo.H
    cv.fill('#000000')
    pale = '#f3e9da'
    with cv.layer(dx=-60 + 120 * drift, scale=1.0 + 0.04 * drift):
        cx = W * 0.5
        cv.rect(cx - W * 0.22, H * 0.7, W * 0.44, H * 0.5, pale, radius=H * 0.18)
        cv.rect(cx - W * 0.05, H * 0.5, W * 0.1, H * 0.26, pale)
        demo.dot(cv, cx, H * 0.38, r=H * 0.2, color=pale)
        demo.dot(cv, cx + H * 0.17, H * 0.42, r=H * 0.06, color=pale)


def _draw(n, cv):
    t = demo.phase(n, 0.4, 1.5)
    amount = 0.65 * (0.5 - 0.5 * math.cos(math.pi * t))  # eases up, then holds
    drift = demo.phase(n, 0.4, demo.SECONDS)
    double_exposure(cv, _landscape, lambda c: _portrait(c, drift), amount)


TECHNIQUE = Technique(
    id='double-exposure',
    name='Double exposure',
    family='vfx',
    group='Dissolves',
    aliases=('superimposition', 'multiple exposure', 'ghost overlay', 'overlay exposure'),
    definition='Two pictures are printed on top of each other, each partly see-through, so you '
               'read both at once as one layered image.',
    phrasings=('overlay a landscape inside a portrait like an old double-exposed photo',
               'put one shot faintly on top of the other so both show through',
               'a ghostly superimposed image of two scenes at the same time'),
    related=('multiples', 'cross-dissolve', 'lens-dirt-overlay', 'blur-up-image-load',
             'image-crossfade-slideshow', 'smoke-overlay'),
    api=('videobuilder.techniques.vfx.double_exposure.double_exposure',),
    demo=lambda: demo.film(_draw),
)

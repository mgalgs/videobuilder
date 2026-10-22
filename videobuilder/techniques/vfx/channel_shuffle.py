"""Channel shuffle: the picture's red, green and blue channels trade places,
so the same image snaps through a run of false-colour versions of itself
(a warm sky goes green, a blue sun goes magenta)."""
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...looks.fx import image_surface, surface_image

ORDERS = ('rgb', 'gbr', 'brg', 'bgr', 'grb', 'rbg')


def shuffle_image(im, order):
    """A PIL RGB image with its channels rearranged: output red, green and
    blue take the input channels named by `order` ('rgb' leaves it alone,
    'bgr' swaps red and blue, 'gbr' rotates them; a repeat such as 'rrb' duplicates one)."""
    order = order.lower()
    if len(order) != 3 or not set(order) <= set('rgb'):
        raise ValueError(f'channel order {order!r} must be three of r, g, b, e.g. "bgr"')
    bands = dict(zip('rgb', im.convert('RGB').split()))
    return Image.merge('RGB', [bands[c] for c in order])


def channel_shuffle(cv, draw, order, to=None, mix=0.0):
    """Draw `draw(c)` onto `cv` with its colour channels rearranged by
    `order` (see `shuffle_image`). With `to` set, cross-fade from `order`
    to the `to` arrangement by `mix` (0 -> 1), for an eased change instead
    of a hard swap. Use it held for a false-colour look, or step `order`
    through `ORDERS` on the beat for a glitch."""
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(sub)
    im = surface_image(sub.surface)
    out = shuffle_image(im, order)
    if to is not None and mix > 0:
        out = Image.blend(out, shuffle_image(im, to), vb.clamp01(mix))
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(out), 0, 0)
    c.paint()
    c.restore()


STEPS = ('rgb', 'gbr', 'brg', 'bgr', 'rgb')
HOLD = 0.6  # seconds per arrangement in the demo


def scene(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def draw(n, cv):
    t = n / demo.FPS
    i = min(int(t / HOLD), len(STEPS) - 1)
    order = STEPS[i]
    channel_shuffle(cv, scene, order)
    f = demo.mono(40, 700)
    label = '  '.join(order.upper())
    w, h = vb.text.block_size([label], f)
    x, y = 40, demo.H - h - 40
    cv.rect(x - 18, y - 12, w + 36, h + 24, demo.BG, radius=12, alpha=0.8)
    vb.text.draw(cv, [label], f, x, y, demo.INK)
    cv.mark('order', x, y, w, h)


TECHNIQUE = Technique(
    id='channel-shuffle',
    name='Channel shuffle',
    family='vfx',
    group='Glitch',
    aliases=('channel swap', 'color channel swap', 'RGB shuffle', 'channel swizzle'),
    definition='The red, green and blue parts of a picture swap places with one another, '
               'so familiar colours flip into strange false-colour versions of the same image.',
    phrasings=('swap the colour channels so the shot turns weird colours',
               'make the picture flick between alien colour versions of itself',
               'trade red and blue in the footage for a glitchy look'),
    related=('color-cycling', 'rgb-split', 'rgb-channel-split', 'grid-reflow-shuffle',
             'theme-swap-crossfade', 'palette-shift-transition'),
    api=('videobuilder.techniques.vfx.channel_shuffle.channel_shuffle',
         'videobuilder.techniques.vfx.channel_shuffle.shuffle_image',
         'videobuilder.techniques.vfx.channel_shuffle.ORDERS'),
    demo=lambda: demo.film(draw),
)

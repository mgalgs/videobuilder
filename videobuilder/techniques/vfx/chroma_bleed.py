"""Chroma bleed: the colour of the picture smears sideways past the edges of
things while the brightness detail stays crisp, like a worn tape or a
low-bandwidth analogue signal."""
import cairo
import numpy as np

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _trailing_box(a, n):
    """Each pixel of `a` (H x W) averaged with the `n` pixels to its left, so
    values drag rightwards; the left edge is padded with its own column."""
    if n < 1:
        return a
    pad = np.concatenate([np.repeat(a[:, :1], n + 1, axis=1), a], axis=1)
    cs = np.cumsum(pad, axis=1)
    return (cs[:, n + 1:] - cs[:, :-n - 1]) / (n + 1)


def chroma_bleed(cv, draw, amount, lag=0.4, saturation=1.15):
    """Draw `draw(c)` onto `cv` with its colour smeared horizontally: the
    picture is split into brightness (kept sharp) and colour difference, the
    colour is dragged `amount` px to the right (a trailing smear) and shifted
    by `lag` x `amount` px, then the two are put back together. `saturation`
    lifts the smeared colour a little so the fringes read. `amount` 0 draws
    the picture untouched. Usable as a held VHS look or animated in and out."""
    if amount <= 0:
        draw(cv)
        return
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sub.fill('#000000')
    draw(sub)
    sub.surface.flush()
    pw, ph = sub.surface.get_width(), sub.surface.get_height()
    stride = sub.surface.get_stride()
    px = np.ndarray((ph, stride // 4, 4), np.uint8, sub.surface.get_data())[:, :pw, :3].astype(np.float32)
    b, g, r = px[..., 0], px[..., 1], px[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb, cr = b - y, r - y
    s = cv.scale
    n = max(1, round(amount * s))
    shift = round(lag * amount * s)
    cb, cr = (_trailing_box(_trailing_box(ch, n // 2), n - n // 2) * saturation for ch in (cb, cr))
    if shift > 0:
        cb = np.concatenate([np.repeat(cb[:, :1], shift, axis=1), cb[:, :-shift]], axis=1)
        cr = np.concatenate([np.repeat(cr[:, :1], shift, axis=1), cr[:, :-shift]], axis=1)
    r2, b2 = y + cr, y + cb
    g2 = (y - 0.299 * r2 - 0.114 * b2) / 0.587
    out = np.empty((ph, pw, 4), np.uint8)
    out[..., 0] = np.clip(b2, 0, 255)
    out[..., 1] = np.clip(g2, 0, 255)
    out[..., 2] = np.clip(r2, 0, 255)
    out[..., 3] = 255
    surf = cairo.ImageSurface.create_for_data(memoryview(out), cairo.FORMAT_ARGB32, pw, ph, pw * 4)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(surf, 0, 0)
    c.paint()
    c.restore()


RED, BLUE, YELLOW = '#e8402f', '#2f6bf0', '#f4c21f'


def _scene(cv):
    cv.fill('#dcd8cf')
    cv.rect(0, demo.H * 0.72, demo.W, demo.H * 0.28, '#2a2a2e')
    for i, color in enumerate((RED, YELLOW, demo.TEAL, BLUE)):
        cx = demo.W * (0.2 + 0.2 * i)
        demo.dot(cv, cx, demo.H * 0.36, r=110, color=color)
        cv.rect(cx - 6, demo.H * 0.36 - 150, 12, 300, '#111111')  # a sharp black bar: luma stays put
    demo.word(cv, 'CHROMA BLEED', demo.W / 2, demo.H * 0.86, size=104, color=RED)


def _draw(n, cv):
    p = demo.phase(n, 0.4, 1.6)
    amount = 55 * p * p * (3 - 2 * p)
    chroma_bleed(cv, _scene, amount)


TECHNIQUE = Technique(
    id='chroma-bleed',
    name='Chroma bleed',
    family='vfx',
    group='VHS & tape',
    aliases=('color bleed', 'colour bleed', 'chroma smear', 'color smear'),
    definition='The colours of a shot slide and smudge sideways beyond the shapes they belong to, '
               'while the outlines and light-and-dark detail stay sharp, like an old videotape.',
    phrasings=('make the colours smear off to the side like a worn VHS tape',
               'let the colour run past the edges but keep the image sharp',
               'give it that blurry analogue colour fringing'),
    related=('watercolor-bleed', 'ink-bleed', 'ink-spread-reveal', 'gradient-wipe', 'smear-frame',
             'light-leak'),
    api=('videobuilder.techniques.vfx.chroma_bleed.chroma_bleed',),
    demo=lambda: demo.film(_draw),
)

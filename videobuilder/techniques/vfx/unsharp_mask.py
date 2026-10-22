"""Unsharp mask: a picture is sharpened by subtracting a blurred copy of itself,
so every edge gets a light rim on its bright side and a dark rim on its dark
side. Pushed hard, those rims become visible halos."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import Canvas
from ...type.kit import blurred


def unsharp_mask(cv, paint, amount=1.5, radius=4.0, threshold=0, box=None):
    """Draw `paint(sub)` into `cv` within `box` (default the whole frame),
    sharpened with an unsharp mask: `amount` is the strength (1.0 = 100 %),
    `radius` the blur in frame px that sets how wide the edge rims are, and
    `threshold` the smallest tonal step (0-255) that gets sharpened, so flat
    areas and grain can be left alone. `sub` is a Canvas in the same frame
    coordinates; draw something opaque into it. An `amount` near 0 draws
    `paint` untouched.

    In a film, wrap any shot: `unsharp_mask(cv, lambda c: shot(c), amount=p * 2)`."""
    box = box or vb.Box.of(cv)
    if amount <= 0.005:
        with cv.clip(box.x, box.y, box.w, box.h):
            paint(cv)
        return
    from PIL import Image, ImageFilter
    s = cv.scale_factor()
    sub = Canvas(box.w, box.h, scale=s)
    sub.ctx.translate(-box.x, -box.y)
    paint(sub)
    sub.surface.flush()
    w, h = sub.surface.get_width(), sub.surface.get_height()
    # cairo's bytes are BGRA; the filter works channel by channel, so the order doesn't matter
    im = Image.frombuffer('RGBA', (w, h), bytes(sub.surface.get_data()), 'raw', 'RGBA', sub.surface.get_stride(), 1)
    im = im.filter(ImageFilter.UnsharpMask(radius=max(0.3, radius * s), percent=round(amount * 100),
                                           threshold=int(threshold)))
    data = bytearray(im.tobytes('raw', 'RGBA'))
    out = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, w * 4)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(box.x, box.y)
    ctx.scale(1 / s, 1 / s)
    ctx.set_source_surface(out, 0, 0)
    ctx.paint()
    ctx.restore()


def _subject(cv):
    """A slightly soft shot full of edges: the photo, a card and a word."""
    W, H = demo.W, demo.H
    img = demo.photo()
    cv.image(img, *vb.Box(0, 0, W, H).cover(img.w, img.h))
    demo.card(cv, W * 0.72, H * 0.68, w=420, h=250, color=demo.TEAL)
    demo.word(cv, 'DETAIL', W / 2, H * 0.36, size=190, color=demo.INK)


def _soft_subject(cv):
    blurred(cv, vb.Box(0, 0, demo.W, demo.H), 3.0, _subject)


def _draw(n, cv):
    W, H = demo.W, demo.H
    p = demo.phase(n, 0.4, 2.5)
    amount = 4.0 * p * p * (3 - 2 * p)
    split = W / 2
    with cv.clip(0, 0, split, H):
        _soft_subject(cv)
    unsharp_mask(cv, _soft_subject, amount=amount, radius=6, box=vb.Box(split, 0, W - split, H))
    cv.line(split, 0, split, H, demo.INK, width=4)
    for x, label in ((40, 'ORIGINAL'), (split + 40, f'UNSHARP MASK  {round(amount * 100)}%')):
        f = demo.mono(30, 700)
        tw = vb.text.measure(label, f)
        cv.rect(x - 14, 34, tw + 28, 58, demo.BG, radius=12, alpha=0.85)
        vb.text.draw(cv, [label], f, x, 44, demo.INK)


TECHNIQUE = Technique(
    id='unsharp-mask',
    name='Unsharp mask',
    family='vfx',
    group='Blend & composite',
    aliases=('USM', 'sharpen filter', 'edge sharpening'),
    definition='A soft image is crisped up by taking away a blurred copy of itself, which brightens the light '
               'side of every edge and darkens the dark side, leaving glowing halos when pushed too far.',
    phrasings=('sharpen this shot so it looks crisper',
               'make the soft footage look less blurry',
               'crank the sharpening until the edges get halos'),
    related=('gaussian-blur', 'blur-dissolve', 'nearest-neighbor-upscale', 'matcap-shading',
             'blur-up-image-load', 'gradient-wipe'),
    api=('videobuilder.techniques.vfx.unsharp_mask.unsharp_mask',),
    demo=lambda: demo.film(_draw),
)

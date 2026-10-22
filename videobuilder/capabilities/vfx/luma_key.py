"""Luma key: a layer's pixels go transparent wherever they are brighter (or
darker) than a threshold, so whatever sits behind shows through its light
areas -- a sky dropping out of a landscape, a black backdrop out of a flame."""
import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _a8(m):
    """An 'L' image -> a cairo A8 surface (rows padded to cairo's stride)."""
    w, h = m.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw, data = m.tobytes(), bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride)


def key_matte(luma, threshold, softness=0.06, key='bright'):
    """The keep-matte for a greyscale 'L' image `luma`: 255 where a pixel
    stays, 0 where it is keyed out. `key='bright'` drops pixels brighter than
    `threshold` (0..1), `key='dark'` drops darker ones (a black key); the
    change is spread over `softness` either side of the threshold (0 is a
    hard edge)."""
    if key not in ('bright', 'dark'):
        raise ValueError(f"luma key: key must be 'bright' or 'dark', not {key!r}")
    s = max(softness, 1e-3)
    sign = 1 if key == 'bright' else -1
    return luma.point([round(255 * vb.clamp01(0.5 + sign * (threshold - v / 255) / (2 * s))) for v in range(256)])


def luma_key(cv, layer, threshold, softness=0.06, key='bright'):
    """Draw `layer(cv)` over what is already on `cv`, with its bright areas
    (`key='bright'`) or dark areas (`key='dark'`) keyed out: a pixel whose
    brightness is past `threshold` (0..1) turns transparent, fading over
    `softness`. Animate `threshold` to eat into the layer tone by tone.

    In a film: draw the background plate, then e.g.
    `luma_key(cv, lambda c: c.image(sky_shot, *box), threshold=0.7)`."""
    c = cv.ctx
    w, h = cv.surface.get_width(), cv.surface.get_height()
    c.push_group()
    layer(cv)
    group = c.pop_group()
    # Flatten the layer to device pixels, so its brightness can be read.
    flat = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    fc = cairo.Context(flat)
    fc.set_matrix(c.get_matrix())  # the group pattern is aligned to the user space it was popped in
    fc.set_source(group)
    fc.paint()
    flat.flush()
    rgba = Image.frombuffer('RGBA', (w, h), bytes(flat.get_data()), 'raw', 'BGRa', flat.get_stride(), 1)
    matte = key_matte(rgba.convert('L'), threshold, softness, key)
    c.save()
    c.identity_matrix()
    c.set_source_surface(flat, 0, 0)
    c.mask_surface(_a8(matte), 0, 0)
    c.restore()


# ---- demo ----

BOX = vb.Box(150, 50, 660, 372)   # where the keyed shot sits
SLIDER = (250, 470, 460)          # x, y, width of the threshold gauge


def _backplate(cv):
    """What the key reveals: a teal plate with a big word, behind the shot."""
    with cv.clip(*BOX):
        cv.fill(demo.TEAL)
        step = 36
        for i in range(-BOX.h // step, BOX.w // step + 2):
            x = BOX.x + i * step
            cv.line(x, BOX.y + BOX.h, x + BOX.h, BOX.y, '#3da897', width=12)
        demo.word(cv, 'BEHIND', BOX.x + BOX.w / 2, BOX.y + BOX.h * 0.32, size=110, color=demo.BG, weight=900)


def _gauge(cv, t):
    """A black-to-white bar with a marker at threshold `t`."""
    x, y, w = SLIDER
    n = 48
    for i in range(n):
        v = round(255 * i / (n - 1))
        cv.rect(x + w * i / n, y, w / n + 0.6, 10, (v, v, v))
    cv.outline(x, y, w, 10, demo.LINE, width=1)
    mx = x + w * t
    demo.dot(cv, mx, y - 12, r=7, color=demo.ACCENT)
    cv.line(mx, y - 6, mx, y + 16, demo.ACCENT, width=2)
    f = demo.mono(18, 600)
    vb.text.draw(cv, [f'key above {t:.2f}'], f, x + w + 22, y - 6, demo.MUTED)


def draw(n, cv):
    t = 1.0 - 0.72 * demo.phase(n, 0.4, 2.6)
    _backplate(cv)
    img = demo.photo()
    luma_key(cv, lambda c: _shot(c, img), t)
    cv.outline(*BOX, demo.LINE, width=2)
    cv.mark('shot', *BOX)
    _gauge(cv, t)


def _shot(cv, img):
    with cv.clip(*BOX):
        cv.image(img, *BOX.cover(img.w, img.h))


CAPABILITY = Capability(
    id='luma-key',
    name='Luma key',
    family='vfx',
    group='Keying & mattes',
    aliases=('luminance key', 'brightness key', 'black key', 'white key'),
    definition='Every part of a layer lighter (or darker) than a chosen brightness turns see-through, '
               'so the layer underneath shows through only those tones.',
    phrasings=('drop out the bright sky so another plate shows through it',
               'make the black background of this clip transparent',
               'cut the layer out by brightness instead of by colour'),
    related=('luma-wipe', 'keystroke-overlay', 'glow-button', 'rim-light', 'spotlight-dim', 'dot-matrix-text'),
    api=('videobuilder.capabilities.vfx.luma_key.luma_key',
         'videobuilder.capabilities.vfx.luma_key.key_matte'),
    demo=lambda: demo.film(draw),
)

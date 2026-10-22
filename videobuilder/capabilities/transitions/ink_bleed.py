"""Ink bleed: the incoming scene soaks through the outgoing one like ink
dropped on wet paper -- a few blots that swell and merge, their ragged edges
creeping outward along the grain, a dark wet rim at the ink's front and a
faint stain running just ahead of it, until the new scene fills the frame."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# Where the ink lands, as (x, y, final radius) in fractions of the frame
# width, and when each blot starts (a fraction of the transition). Together
# they cover the frame just before the end.
BLOTS = ((0.34, 0.42, 0.37, 0.0), (0.72, 0.62, 0.33, 0.12), (0.14, 0.86, 0.23, 0.28),
         (0.86, 0.14, 0.22, 0.36))


def _smooth(lo, hi):
    """A 256-entry lookup: 0 below `lo`, 255 above `hi`, smoothstep between."""
    out = []
    for v in range(256):
        t = min(1.0, max(0.0, (v - lo) / (hi - lo)))
        out.append(round(255 * t * t * (3 - 2 * t)))
    return out


_INSIDE = _smooth(124, 140)                                  # the ink itself
_RIM = [min(255, 2 * min(a, 255 - b)) for a, b in zip(_smooth(122, 134), _smooth(142, 176))]  # its wet front
_FLOOR = [min(255, max(0, (v - 128) * 2 + 128 - 110)) for v in range(256)]
_CEIL = [min(255, max(0, (v - 128) * 2 + 128 + 110)) for v in range(256)]
_STAIN = [round(v * 0.22) for v in _smooth(96, 128)]         # the damp ring running ahead


def _gain(img, k):
    """`img`'s swing about 128 multiplied by `k`."""
    return img.point([min(255, max(0, round(128 + (v - 128) * k))) for v in range(256)])


@lru_cache(maxsize=8)
def _grain(w, h, seed):
    """Static paper-fibre noise around 128: broad lumps plus fine fibres, so
    the edge wanders and throws out little tendrils."""
    rnd = random.Random(seed)
    out = Image.new('L', (w, h), 128)
    for cells, weight in ((14, 1.0), (45, 0.5), (160, 0.3)):  # cells across the frame
        cw, ch = cells, max(2, round(cells * h / w))
        n = Image.new('L', (cw, ch))
        n.putdata([rnd.randrange(256) for _ in range(cw * ch)])
        n = n.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w / cells / 3))
        out = ImageChops.add(out, _gain(n, weight), offset=-128)
    return _gain(out, 34 / max(1.0, ImageStat.Stat(out).stddev[0]))


def _field(w, h, p, blots, seed):
    """The ink's density field at progress `p`, 0-255 with the edge at ~128."""
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    for bx, by, r, t0 in blots:
        k = vb.clamp01((p - t0) / (1 - t0) if t0 < 1 else 0)
        if k <= 0:
            continue
        # Ink soaks like diffusion, its radius growing with the square root of time:
        # a quick spread that slows as it goes.
        rr = w * (r * math.sqrt(k) + 0.01)
        d.ellipse((bx * w - rr, by * h - rr, bx * w + rr, by * h + rr), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(w * 0.04))
    # The paper's grain pushes the edge in and out (harder as the ink soaks),
    # but only near the edge: deep inside stays inked, far outside stays dry.
    field = ImageChops.add(m, _gain(_grain(w, h, seed), 0.8 + 0.5 * p), offset=-128)
    field = ImageChops.lighter(field, m.point(_FLOOR))
    return ImageChops.darker(field, m.point(_CEIL))


def _a8(img):
    w, h = img.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw, data = img.tobytes(), bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride)


def _paint(cv, source, alpha_img, dev_w, dev_h):
    """Paint `source` (a cairo source setter) over the whole frame through
    `alpha_img`, a small L image stretched smoothly to the frame."""
    ctx = cv.ctx
    surf = _a8(alpha_img)
    pat = cairo.SurfacePattern(surf)
    pat.set_filter(cairo.FILTER_GOOD)
    pat.set_extend(cairo.EXTEND_PAD)
    pat.set_matrix(cairo.Matrix(xx=alpha_img.size[0] / dev_w, yy=alpha_img.size[1] / dev_h))
    ctx.save()
    ctx.identity_matrix()
    source(ctx)
    ctx.mask(pat)
    ctx.restore()


def ink_bleed(cv, a, b, p, ink='#15131a', blots=BLOTS, seed=7):
    """Draw the bleed at progress `p` (0 -> 1): `a(cv)` underneath, with `b`
    showing through blots of ink that swell and merge across it. `ink`
    colours the wet rim and the damp stain ahead of it; `blots` are
    (x, y, final radius, start) in fractions of the frame width / of the
    transition; `seed` picks the paper grain.

    In a film, call it while two shots are live in an overlap, e.g.
    `ink_bleed(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if p <= 0:
        return a(cv)
    if p >= 1:
        return b(cv)
    dev_w, dev_h = cv.surface.get_width(), cv.surface.get_height()
    w = max(48, round(dev_w / 2))
    h = max(27, round(w * dev_h / dev_w))
    field = _field(w, h, p, blots, seed)
    a(cv)
    # The damp stain ahead of the ink, then the incoming scene through the ink, then its rim.
    _paint(cv, lambda c: c.set_source_rgba(*vb.canvas.rgba(ink)), field.point(_STAIN), dev_w, dev_h)
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    b(sub)
    sub.surface.flush()
    _paint(cv, lambda c: c.set_source_surface(sub.surface, 0, 0), field.point(_INSIDE), dev_w, dev_h)
    wet = 0.85 * (1 - vb.clamp01((p - 0.8) / 0.2))  # the wet front dries off as the frame fills
    _paint(cv, lambda c: c.set_source_rgba(*vb.canvas.rgba(ink, wet)), field.point(_RIM), dev_w, dev_h)


TECHNIQUE = Technique(
    id='ink-bleed',
    name='Ink bleed',
    family='transitions',
    group='Organic and Fluid',
    aliases=('ink transition', 'ink drop reveal', 'bleed-through transition'),
    definition='The next scene seeps in through spreading blots of ink whose dark, ragged edges creep '
               'outward and merge, as if soaking into paper, until it covers the frame.',
    phrasings=('make the next shot soak in like ink spreading on paper',
               'an inky blot transition with wet ragged edges',
               'have scene two bleed through scene one like spilled ink'),
    related=('ink-spread-reveal', 'ink-splash-spread', 'watercolor-bleed', 'chroma-bleed', 'ink-in-water',
             'ink-outline'),
    api=('videobuilder.techniques.transitions.ink_bleed.ink_bleed',),
    demo=lambda: demo.two_scenes(ink_bleed, start=0.6, length=1.9),
)

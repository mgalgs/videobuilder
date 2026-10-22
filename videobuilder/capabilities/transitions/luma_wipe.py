"""Luma wipe: the incoming scene appears wherever a greyscale map is darker
than a rising threshold, so the cut spreads in the map's own shapes -- dark
patches first, bright ones last -- with a soft edge where the threshold sits."""
import random

import cairo
from PIL import Image, ImageFilter, ImageOps

from .. import _demo as demo
from ..schema import Capability

_CLOUDS = {}  # (w, h, seed) -> 'L' image


def clouds_matte(w, h, seed=7):
    """A soft cloudy greyscale map, `w` x `h` px, as a PIL 'L' image: a few
    octaves of smoothed noise, equalised so every grey level covers about the
    same area (the wipe then uncovers the frame at an even rate). Built once
    per size and seed."""
    key = (w, h, seed)
    if key not in _CLOUDS:
        rnd = random.Random(seed)
        acc = Image.new('L', (w, h), 128)
        for i, cell in enumerate((5, 11, 23)):
            nw, nh = max(2, cell * w // max(w, h)), max(2, cell * h // max(w, h))
            noise = Image.frombytes('L', (nw, nh), rnd.randbytes(nw * nh)).resize((w, h), Image.BICUBIC)
            acc = Image.blend(acc, noise, 0.6 / (i + 1))
        _CLOUDS[key] = ImageOps.equalize(acc.filter(ImageFilter.GaussianBlur(max(1, w // 160))))
    return _CLOUDS[key]


def _a8(m):
    """An 'L' image -> a cairo A8 surface (rows padded to cairo's stride)."""
    w, h = m.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw, data = m.tobytes(), bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride)


def luma_wipe(cv, a, b, p, matte=None, softness=0.2, invert=False):
    """Draw the luma wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` shown through a mask taken from the greyscale `matte` -- a pixel
    of `b` turns on once `p` passes its brightness, fading in over `softness`
    (0 is a hard edge). `matte` is a PIL image (any mode; it is greyscaled and
    stretched over the frame) or None for `clouds_matte`; a radial or linear
    gradient gives a shaped wipe, a photo or texture an organic one.
    `invert`: bright areas go first.

    In a film, call it while two shots are live in an overlap, e.g.
    `luma_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.surface.get_width(), cv.surface.get_height()
    m = clouds_matte(w, h) if matte is None else matte.convert('L').resize((w, h), Image.BILINEAR)
    if invert:
        m = ImageOps.invert(m)
    # Threshold runs from -softness to 1 so the first and last pixels both get a full fade.
    s = max(softness, 1e-3)
    t = p * (1 + s) - s
    mask = m.point([round(255 * min(1.0, max(0.0, (t - v / 255) / s + 1))) for v in range(256)])
    a(cv)
    c = cv.ctx
    c.push_group()
    b(cv)
    c.pop_group_to_source()
    c.save()
    c.identity_matrix()  # the mask is in device px; the source stays locked to the user space it was set in
    c.mask_surface(_a8(mask), 0, 0)
    c.restore()


CAPABILITY = Capability(
    id='luma-wipe',
    name='Luma wipe',
    family='transitions',
    group='Wipes',
    aliases=('gradient wipe', 'luminance wipe', 'matte wipe', 'luma fade'),
    definition='The next scene seeps in through a greyscale pattern, darkest areas first and lightest last, '
               'so the changeover takes on the pattern\'s shapes.',
    phrasings=('reveal the next shot through a cloudy texture instead of a straight line',
               'use a black-and-white gradient to control how the scenes swap',
               'an organic, blotchy wipe between the two clips'),
    related=('logo-mask-wipe-reveal', 'difference-highlight', 'luma-key', 'paint-brush-wipe', 'area-fill-sweep',
             'flash-cut'),
    api=('videobuilder.capabilities.transitions.luma_wipe.luma_wipe',
         'videobuilder.capabilities.transitions.luma_wipe.clouds_matte'),
    demo=lambda: demo.two_scenes(luma_wipe, start=0.6, length=1.8),
)

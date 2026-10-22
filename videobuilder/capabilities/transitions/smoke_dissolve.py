"""Smoke Dissolve: a front of soft, billowing smoke drifts across the
outgoing scene, and the incoming scene shows through wherever the smoke
has thinned, so one picture seems to burn off into the next."""
import random
from functools import lru_cache

import cairo
from PIL import Image, ImageChops, ImageFilter, ImageOps

from .. import _demo as demo
from ..schema import Technique

FIELD = 6  # the smoke field is worked out at 1/FIELD of the frame's size, then smoothed up


@lru_cache(maxsize=8)
def _billows(w, h, seed):
    """Seeded cloudy grey noise, w x h: three octaves of value noise, coarse
    to fine, stretched over the full 0..255 range. Cached."""
    rnd = random.Random(seed)
    out = None
    for cell, weight in ((24, 1.0), (10, 0.4), (4, 0.18)):
        nw, nh = max(2, w // cell), max(2, h // cell)
        octave = Image.frombytes('L', (nw, nh), rnd.randbytes(nw * nh)).resize((w, h), Image.BICUBIC)
        out = octave if out is None else Image.blend(out, octave, weight / (1 + weight))
    return ImageOps.autocontrast(out.filter(ImageFilter.GaussianBlur(1.2)), cutoff=1)


@lru_cache(maxsize=4)
def _ramp(w, h, slant):
    """A grey ramp, 0 at the left edge to 255 at the right, leaning by
    `slant` (a fraction of the width across the full height)."""
    row = Image.linear_gradient('L').rotate(90).resize((w, 1))  # 0 at the left
    out = Image.new('L', (w, h))
    for y in range(h):
        shift = round(slant * w * (y / max(1, h - 1) - 0.5))
        out.paste(row.transform((w, 1), Image.AFFINE, (1, 0, shift, 0, 1, 0), Image.BILINEAR,
                                fillcolor=0 if shift < 0 else 255), (0, y))
    return out


def _drift(im, w, h, dx, dy):
    """A w x h window of `im` slid by (dx, dy) field px, sub-pixel smooth."""
    return im.transform((w, h), Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)


def _pattern(mask, cv):
    """An L image as a cairo alpha pattern stretched smoothly over the whole canvas."""
    w, h = mask.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw, data = mask.tobytes(), bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    pat = cairo.SurfacePattern(cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride))
    m = cairo.Matrix()
    m.scale(w / cv.width, h / cv.height)
    pat.set_matrix(m)
    pat.set_extend(cairo.EXTEND_PAD)
    pat.set_filter(cairo.FILTER_GOOD)
    return pat


def smoke_masks(width, height, p, seed=3, softness=0.22, slant=0.25, drift=0.35):
    """The two masks behind a smoke dissolve at progress `p` (0 -> 1), as L
    images 1/FIELD the size of a `width` x `height` frame: `(reveal, smoke)`.
    `reveal` is 255 where the incoming scene shows; `smoke` is the haze along
    the moving front. `softness` is how ragged and wide the front is (a
    fraction of the noise range), `slant` how far it leans, `drift` how far
    the billows themselves travel across the transition (a fraction of the width)."""
    fw, fh = max(8, round(width / FIELD)), max(8, round(height / FIELD))
    big = _billows(fw * 2, fh * 2, seed)
    body = _drift(big, fw, fh, fw * 0.3 + fw * drift * (1 - p), fh * 0.4 + fh * 0.12 * p)
    wisps = _drift(big, fw, fh, fw * 0.9 - fw * drift * 1.6 * p, fh * 0.9 - fh * 0.2 * p)
    density = Image.blend(_ramp(fw, fh, slant), body, 0.5)
    soft = 255 * softness
    level = -soft + p * (255 + 2 * soft)  # the front: everything denser than this is still scene A
    reveal = density.point([round(255 * min(1.0, max(0.0, (level - v) / soft + 0.5))) for v in range(256)])
    edge = [round(255 * max(0.0, 1 - ((v - level) / (1.6 * soft)) ** 2)) for v in range(256)]
    smoke = ImageChops.multiply(density.point(edge), ImageOps.autocontrast(Image.blend(body, wisps, 0.5)))
    return reveal, smoke


def smoke_dissolve(cv, a, b, p, color='#d9d6cf', opacity=0.9, **kw):
    """Draw the dissolve at progress `p` (0 -> 1): `a(cv)` drifting into
    smoke of `color`, `b(cv)` showing through where it clears. `kw` goes to
    `smoke_masks` (`seed`, `softness`, `slant`, `drift`).

    In a film, call it while two shots are live in an overlap, e.g.
    `smoke_dissolve(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    reveal, smoke = smoke_masks(cv.width, cv.height, p, **kw)
    a(cv)
    c = cv.ctx
    c.save()
    c.push_group()
    b(cv)
    c.pop_group_to_source()
    c.mask(_pattern(reveal, cv))
    r, g, bl = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    c.set_source_rgba(r, g, bl, opacity)
    c.mask(_pattern(smoke, cv))
    c.restore()


TECHNIQUE = Technique(
    id='smoke-dissolve',
    name='Smoke dissolve',
    family='transitions',
    group='Organic and Fluid',
    aliases=('smoke transition', 'fog wipe', 'smoke wipe'),
    definition='A ragged bank of drifting smoke rolls across the shot, and the next scene '
               'appears wherever the smoke thins out behind it.',
    phrasings=('make the first scene blow away like smoke into the second',
               'a foggy, wispy transition where the new shot clears through the haze',
               'let the picture vanish in a puff of smoke and reveal what comes next'),
    related=('smoke-overlay', 'smoke-puffs', 'noise-dissolve', 'layered-fog-bands', 'heat-haze', 'drip-wipe'),
    api=('videobuilder.techniques.transitions.smoke_dissolve.smoke_dissolve',
         'videobuilder.techniques.transitions.smoke_dissolve.smoke_masks'),
    demo=lambda: demo.two_scenes(smoke_dissolve, start=0.6, length=1.9),
)

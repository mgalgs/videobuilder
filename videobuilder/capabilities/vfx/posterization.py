"""Posterization: each colour channel is cut down to a few tonal steps, so
smooth gradients break into flat bands with hard edges between them."""
import math
from functools import lru_cache

from PIL import Image as PILImage

import videobuilder as vb

from ...looks import fx
from .. import _demo as demo
from ..schema import Technique


def posterize_levels(im, levels):
    """The PIL image `im` (RGB) with each channel snapped to `levels` evenly
    spaced values (2 = pure on/off per channel; 256 leaves it unchanged)."""
    levels = max(2, min(256, int(levels)))
    step = 255 / (levels - 1)
    lut = [round(round(v / step) * step) for v in range(256)]
    return im.point(lut * 3)


def posterized(cv, levels, box=None):
    """A context manager: everything drawn on `cv` inside the block (and what
    was there already) comes out posterized to `levels` steps per channel,
    over the whole frame or only `box` (x, y, w, h). Draw copy that must stay
    readable after the block.

        with posterized(cv, 4):
            draw_the_shot(n, cv)"""
    flt = fx.Filter('posterization', 'Posterization', 'colour cut to a few flat tonal steps',
                    lambda im, t, age, u: posterize_levels(im, levels))
    return fx.apply(cv, flt, 0.0, box=box)


STEPS = (256, 16, 8, 5, 4, 3)   # levels per channel, one after another (256: untouched)


@lru_cache(maxsize=1)
def _subject(w=640, h=360):
    """A smooth-shaded subject, made in code: a dusk sky fading top to bottom
    and a lit sphere on it -- all soft gradients, where the bands show best."""
    sky_top, sky_low = (28, 40, 110), (250, 150, 90)
    cx, cy, r = w * 0.5, h * 0.52, h * 0.36
    lx, ly = cx - r * 0.4, cy - r * 0.45            # the highlight
    data = bytearray()
    for y in range(h):
        t = y / (h - 1)
        sky = [a + (b - a) * t for a, b in zip(sky_top, sky_low)]
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            if d < r:
                lit = 1 - min(1.0, math.hypot(x - lx, y - ly) / (r * 1.5))
                c = [40 + 215 * lit ** 1.4, 170 * lit + 60 * lit ** 3, 150 + 90 * lit]
                edge = min(1.0, r - d)                  # a one-pixel soft rim
                c = [s + (v - s) * edge for s, v in zip(sky, c)]
            else:
                c = sky
            data += bytes(max(0, min(255, round(v))) for v in c)
    return vb.Image.from_pil(PILImage.frombytes('RGB', (w, h), bytes(data)))


def _shot(cv):
    img = _subject()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def draw(n, cv):
    i = min(len(STEPS) - 1, int(demo.phase(n, 0.5, 2.6) * len(STEPS)))
    levels = STEPS[i]
    with posterized(cv, levels):
        _shot(cv)
    label = 'full tone' if levels >= 256 else f'{levels} levels'
    cv.rect(demo.W - 360, demo.H - 130, 300, 80, demo.BG, radius=16, alpha=0.85)
    demo.word(cv, label, demo.W - 210, demo.H - 90, size=44, weight=700)


TECHNIQUE = Technique(
    id='posterization',
    name='Posterization',
    family='vfx',
    group='Dithering & quantization',
    aliases=('posterize', 'tone banding', 'colour banding'),
    definition='The picture is limited to a handful of tones per colour, so smooth shading '
               'turns into flat bands of colour with hard steps between them.',
    phrasings=('make the image look like a screen print with only a few flat colours',
               'crush the gradients into chunky colour bands',
               'cut the photo down to a few tones, poster style'),
    related=('pixelation', 'solarization', 'desaturation', 'blur-up-image-load', 'pixelate-transition',
             'kinetic-poster-layout'),
    api=('videobuilder.techniques.vfx.posterization.posterized',
         'videobuilder.techniques.vfx.posterization.posterize_levels'),
    demo=lambda: demo.film(draw),
)

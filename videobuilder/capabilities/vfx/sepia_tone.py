"""Sepia tone: the colour drains out of a picture and its light and shade
come back in warm browns -- deep umber shadows, tan mid-tones, cream
highlights -- like an old toned print."""
from functools import lru_cache

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ...canvas import rgba
from ...looks.fx import Filter, apply
from ..schema import Technique

# the toning ramp, darkest first: where black, the mid-grey and white land
SHADOW, MID, HIGHLIGHT = '#1e120a', '#8a6440', '#f6ead0'


@lru_cache(maxsize=16)
def _ramp(dark, mid, light):
    """Three 256-entry lookup tables (R, G, B) running from `dark` through
    `mid` to `light` as brightness goes from 0 to 255."""
    stops = [[255 * ch for ch in rgba(c)[:3]] for c in (dark, mid, light)]
    tables = ([], [], [])
    for v in range(256):
        f = v / 255 * 2
        a, b = (stops[0], stops[1]) if f <= 1 else (stops[1], stops[2])
        f = f if f <= 1 else f - 1
        for ch in range(3):
            tables[ch].append(round(a[ch] + (b[ch] - a[ch]) * f))
    return tables


def sepia(im, amount=1.0, shadow=SHADOW, mid=MID, highlight=HIGHLIGHT):
    """`im` (a PIL image) toned sepia: its brightness mapped onto the warm
    ramp `shadow` -> `mid` -> `highlight`, mixed with the original by
    `amount` (0 leaves it as it is, 1 is fully toned). Returns an RGB image
    the same size."""
    im = im.convert('RGB')
    if amount <= 0:
        return im
    gray = im.convert('L')
    toned = Image.merge('RGB', [gray.point(t) for t in _ramp(shadow, mid, highlight)])
    return toned if amount >= 1 else Image.blend(im, toned, amount)


FILTER = Filter('sepia-tone', 'Sepia tone', 'colour drained into warm browns, like an old print',
                lambda im, t, age, u, amount=1.0, **ramp: sepia(im, amount, **ramp))


def sepia_tone(cv, amount=1.0, box=None, **ramp):
    """A context manager: everything on `cv` -- what is drawn inside the
    block and what was there already -- comes out sepia-toned by `amount`
    (0 -> 1) when the block ends, the whole frame or only `box` (x, y, w, h).
    `ramp` may set `shadow`, `mid` and `highlight` colours.

        with sepia_tone(cv, ease(p)):
            draw_the_scene(cv)
    """
    return apply(cv, FILTER, 0.0, box=box, opts=dict(amount=amount, **ramp))


def draw(n, cv):
    amount = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.9))
    with sepia_tone(cv, amount):
        img = demo.photo()
        cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


TECHNIQUE = Technique(
    id='sepia-tone',
    name='Sepia tone',
    family='vfx',
    group='Color & grading',
    aliases=('sepia', 'sepia filter', 'vintage brown tint', 'old photo look'),
    definition='A picture loses its colour and is redrawn in warm browns, dark umber in the shadows '
               'and pale cream in the highlights, so it looks like an aged photograph.',
    phrasings=('make the footage look like an old brown photo',
               'turn the shot into a vintage sepia print',
               'fade the colour out to that warm antique brown'),
    related=('halftone', 'rgb-channel-split', 'chromatic-dispersion', 'gooch-shading',
             'cel-shading-look', 'night-vision'),
    api=('videobuilder.techniques.vfx.sepia_tone.sepia_tone',
         'videobuilder.techniques.vfx.sepia_tone.sepia'),
    demo=lambda: demo.film(draw),
)

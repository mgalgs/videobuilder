"""Oil paint filter: a Kuwahara filter. Every pixel takes the average colour
of whichever of the four squares around it varies least, so flat areas melt
into smooth dabs of colour while edges between them stay crisp -- a picture
that looks laid down with a loaded brush."""
from contextlib import contextmanager

import numpy as np
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...looks import fx


def _box_sums(a, k):
    """Sums of `a` (h x w x c) over every k x k window, indexed by the window's
    top-left corner: shape (h - k + 1, w - k + 1, c)."""
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1, a.shape[2]))
    s[1:, 1:] = a.cumsum(0).cumsum(1)
    return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]


def kuwahara(im, radius):
    """`im` (a PIL image) oil-painted: each pixel becomes the mean colour of
    the least varied of the four (radius + 1)-px squares that have it as a
    corner. `radius` is in pixels of `im`; 0 returns `im` unchanged."""
    r = int(round(radius))
    im = im.convert('RGB')
    if r < 1:
        return im
    h, w = im.height, im.width
    rgb = np.asarray(im, dtype=np.float64)
    pad = np.pad(rgb, ((r, r), (r, r), (0, 0)), mode='edge')
    luma = pad @ np.array([0.299, 0.587, 0.114])
    k = r + 1
    n = k * k
    sums = _box_sums(pad, k)
    lum = _box_sums(np.stack([luma, luma * luma], axis=-1), k)
    best_var = np.full((h, w), np.inf)
    out = np.zeros((h, w, 3))
    for dy in (0, r):            # the four quadrants: top-left corner offsets in the padded image
        for dx in (0, r):
            m = lum[dy:dy + h, dx:dx + w]
            var = m[..., 1] / n - (m[..., 0] / n) ** 2
            better = var < best_var
            best_var = np.where(better, var, best_var)
            out[better] = sums[dy:dy + h, dx:dx + w][better] / n
    return PILImage.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), 'RGB')


def _treat(im, t, age, u, radius=8.0):
    return kuwahara(im, radius * u)


FILTER = fx.Filter('oil-paint', 'Oil paint filter', 'smooth brushlike patches, crisp edges', _treat)


@contextmanager
def oil_paint(cv, radius=8.0, box=None):
    """Everything drawn inside the block is oil-painted on the way out:

        with oil_paint(cv, radius=10):
            cv.image(photo, 0, 0, W, H)

    `radius` is the brush size in px of a 1080-high frame (scaled with the
    canvas, so previews match); 0 leaves the picture untouched. `box`
    (x, y, w, h) limits the treatment to that region."""
    if radius <= 0:
        yield cv
        return
    with fx.apply(cv, FILTER, 0.0, box=box, opts={'radius': radius}):
        yield cv


MAX_RADIUS = 16
_PHOTO = None


def _textured_photo():
    """The kit's photo with grain, mottling and fine hatching laid over it:
    a flat picture gives the filter nothing to smooth, a busy one shows the
    dabs forming."""
    global _PHOTO
    if _PHOTO is None:
        base = demo.photo()._pil.convert('RGB')
        w, h = base.size
        rng = np.random.default_rng(7)
        a = np.asarray(base, dtype=np.float64)
        blotch = np.asarray(PILImage.fromarray(rng.integers(0, 256, (h // 24 + 1, w // 24 + 1), dtype=np.uint8))
                            .resize((w, h), PILImage.BICUBIC), dtype=np.float64) - 128
        ys, xs = np.mgrid[0:h, 0:w]
        hatch = np.sin((xs + ys) * 0.9) * np.sin((xs - ys) * 0.35)
        grain = rng.normal(0, 1, (h, w))
        a += (0.18 * blotch + 18 * hatch + 22 * grain)[..., None] * np.array([1.0, 0.95, 0.85])
        _PHOTO = vb.Image.from_pil(PILImage.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB'))
    return _PHOTO


def draw(n, cv):
    img = _textured_photo()
    x, y, w, h = vb.Box.of(cv).cover(img.w, img.h)
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.2))
    radius = round(MAX_RADIUS * p)      # whole px steps, so the brush grows in visible notches
    with oil_paint(cv, radius):
        cv.image(img, x, y, w, h)
    cv.mark('photo', x, y, w, h)


TECHNIQUE = Technique(
    id='oil-paint-filter',
    name='Oil paint filter',
    family='vfx',
    group='Painterly & sketch',
    aliases=('Kuwahara filter', 'oil painting effect', 'brush smoothing'),
    definition='A picture is redrawn as soft, flat dabs of colour with sharp borders between them, '
               'as though painted with a thick brush, and the dabs grow larger as the effect strengthens.',
    phrasings=('make the photo look like an oil painting',
               'turn the footage into brushy painted patches but keep the edges sharp',
               'give this shot a painterly smeared look'),
    related=('unsharp-mask', 'gooey-filter', 'liquify', 'heat-haze', 'emboss', 'ken-burns-effect'),
    api=('videobuilder.techniques.vfx.oil_paint_filter.oil_paint',
         'videobuilder.techniques.vfx.oil_paint_filter.kuwahara'),
    demo=lambda: demo.film(draw),
)

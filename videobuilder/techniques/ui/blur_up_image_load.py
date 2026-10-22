"""Blur-up image load: a soft, low-detail placeholder stands in for an image,
then sharpens smoothly into the full picture once it has arrived."""
from functools import lru_cache

from PIL import ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

LEVELS = 6  # blur steps from the placeholder down to sharp; drawing crossfades between neighbours


@lru_cache(maxsize=16)
def _blur_levels(img, blur, levels):
    """`img` at `levels` + 1 strengths: index 0 sharp, the last the
    placeholder. The placeholder is the image shrunk to a few dozen pixels and
    blurred, like a tiny preview stretched to size; the steps between lose
    an equal share of the blur each, so the sharpening reads even. Built once
    per image."""
    pil = img._pil
    sigma = blur * img.w
    out = [img] + [vb.Image.from_pil(pil.filter(ImageFilter.GaussianBlur(sigma * k / levels)))
                   for k in range(1, levels)]
    tiny = pil.resize((max(4, img.w // 24), max(4, img.h // 24)))
    out.append(vb.Image.from_pil(tiny.resize((img.w, img.h)).filter(ImageFilter.GaussianBlur(sigma))))
    return tuple(out)


def blur_up(cv, img, x, y, w, h, p, blur=0.04, radius=0, levels=LEVELS):
    """Draw `img` in the box (x, y, w, h) loading at progress `p`: 0 is the
    blurred placeholder, 1 the sharp image, in between it sharpens through
    `levels` blur steps. `blur` is the placeholder's blur as a fraction of
    the image width; `radius` rounds the box's corners.

    In a film, hold `p` at 0 while the image is "loading", then run it 0 -> 1
    over about a second, e.g. `blur_up(cv, photo, *box, vb.ease_out_quint(t))`."""
    stack = _blur_levels(img, float(blur), int(levels))
    pos = (1 - vb.clamp01(p)) * levels  # levels .. 0
    lo = int(pos)
    frac = pos - lo
    with cv.clip(x, y, w, h, radius=radius):
        cv.image(stack[lo], x, y, w, h)
        if frac > 0:
            cv.image(stack[lo + 1], x, y, w, h, alpha=frac)


def draw(n, cv):
    img = demo.photo()
    w = 520
    h = w * img.h / img.w
    x, y = (demo.W - w) / 2, (demo.H - h) / 2 - 16
    cv.shadow(x, y, w, h, radius=16, dy=10, blur=30, color=(0, 0, 0, 0.5))
    blur_up(cv, img, x, y, w, h, vb.ease_in_out_quart(demo.phase(n, 0.9, 2.5)), radius=16)
    loading = 1 - demo.phase(n, 0.8, 1.1)
    if loading > 0:  # a small loading bar under the placeholder, gone once the image lands
        bx, by, bw = demo.W / 2 - 90, y + h + 28, 180
        cv.rect(bx, by, bw, 4, demo.LINE, radius=2, alpha=loading)
        cv.rect(bx, by, bw * demo.phase(n, 0.0, 0.85), 4, demo.ACCENT, radius=2, alpha=loading)
    cv.mark('image', x, y, w, h)


TECHNIQUE = Technique(
    id='blur-up-image-load',
    name='Blur-up image load',
    family='ui',
    group='Layout & lists',
    aliases=('progressive image load', 'low-quality image placeholder', 'LQIP', 'blur-up'),
    definition='A picture first shows as a soft, smeared preview, then comes into focus '
               'as the real image finishes loading.',
    phrasings=('the photo starts out blurry and sharpens once it loads',
               'show a fuzzy placeholder that resolves into the full image',
               'images that fade from a blurred preview into crisp detail'),
    related=('gaussian-blur', 'pixelation', 'zoom-blur', 'blur-dissolve', 'spin-blur',
             'nearest-neighbor-upscale'),
    api=('videobuilder.techniques.ui.blur_up_image_load.blur_up',),
    demo=lambda: demo.film(draw),
)

"""Image Crossfade Slideshow: a gallery window where each picture holds, then
the next one dissolves in over it in place -- nothing slides or moves."""
import random

from PIL import Image as PILImage, ImageDraw

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def crossfade_slideshow(cv, slides, box, t, hold=1.0, fade=0.5, radius=0, loop=False, ease=vb.ease_in_out_quart):
    """Draw a crossfading slideshow into `box` (x, y, w, h) at time `t` seconds.

    `slides` are `vb.Image`s (drawn to cover the box) or callables
    `slide(cv, box)`. Each slide holds for `hold` seconds, then the next fades
    in on top of it over `fade` seconds. Past the last slide it holds there,
    or with `loop` wraps back to the first. Clipped to the box with corner
    `radius`. Returns `(index, p)`: the slide showing (or fading out) and the
    fade's eased progress 0 -> 1."""
    n = len(slides)
    step = hold + fade
    k, into = divmod(max(0.0, t), step)
    k = int(k)
    if not loop and k >= n - 1:
        k, p = n - 1, 0.0
    else:
        p = ease(vb.clamp01((into - hold) / fade)) if fade > 0 else float(into >= hold)
    box = vb.Box(*box)
    with cv.clip(*box, radius):
        _slide(cv, slides[k % n], box)
        if p > 0:
            with cv.layer(opacity=p):
                _slide(cv, slides[(k + 1) % n], box)
    return k % n, p


def _slide(cv, slide, box):
    if callable(slide):
        slide(cv, box)
    else:
        cv.image(slide, *box.cover(slide.w, slide.h))


# Three plainly different procedural photos (a dusk, a noon and a night
# landscape), built once in code so no binary asset ships.
_PALETTES = (
    ((31, 94, 86), (233, 142, 88), (255, 219, 168), (18, 48, 44)),
    ((70, 140, 220), (190, 225, 245), (255, 245, 200), (60, 120, 70)),
    ((16, 18, 52), (70, 50, 110), (235, 235, 255), (28, 26, 60)),
)
_PHOTOS = None


def _photo(top, bottom, sun, hill, seed, w=640, h=420):
    rnd = random.Random(seed)
    grad = PILImage.new('RGB', (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((w, h))
    d = ImageDraw.Draw(img)
    sx, sy, sr = w * rnd.uniform(0.2, 0.8), h * rnd.uniform(0.2, 0.35), w * 0.09
    d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=sun)
    for i in range(3):
        cx, r = w * (0.15 + 0.38 * i + rnd.uniform(-0.08, 0.08)), w * rnd.uniform(0.24, 0.34)
        shade = tuple(max(0, c - 12 * i) for c in hill)
        d.ellipse((cx - r, h * 0.84 - r * 0.6, cx + r, h * 0.84 + r * 1.4), fill=shade)
    return vb.Image.from_pil(img)


def _photos():
    global _PHOTOS
    if _PHOTOS is None:
        _PHOTOS = [_photo(*pal, seed=i) for i, pal in enumerate(_PALETTES)]
    return _PHOTOS


def draw(n, cv):
    photos = _photos()
    w, h = 640, 400
    box = vb.Box(demo.W / 2 - w / 2, demo.H / 2 - h / 2 - 20, w, h)
    cv.shadow(*box, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    k, p = crossfade_slideshow(cv, photos, box, n / demo.FPS, hold=0.6, fade=0.6, radius=18)
    # Position dots under the frame; the active one hands over with the fade.
    y = box.y + box.h + 34
    for i in range(len(photos)):
        on = (1 - p) if i == k else p if i == (k + 1) % len(photos) else 0.0
        demo.dot(cv, demo.W / 2 + (i - 1) * 32, y, r=6 + 2 * on, color=demo.kit.mix(demo.MUTED, demo.INK, on))


CAPABILITY = Capability(
    id='image-crossfade-slideshow',
    name='Image crossfade slideshow',
    family='ui',
    group='Cards & media',
    aliases=('fade gallery', 'crossfade carousel', 'dissolve slideshow'),
    definition='A gallery that shows one picture at a time, and to move on, the next picture '
               'fades in right on top of the current one instead of sliding across.',
    phrasings=('a photo slideshow where each picture fades into the next',
               'a carousel that dissolves between images rather than swiping',
               'cycle through some pictures with soft fades in the same frame'),
    related=('cross-dissolve', 'carousel-slide', 'cross-zoom', 'theme-swap-crossfade', 'view-transition',
             'parallax-slide'),
    api=('videobuilder.capabilities.ui.image_crossfade_slideshow.crossfade_slideshow',),
    demo=lambda: demo.film(draw),
)

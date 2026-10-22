"""Pixel sorting: every run of pixels brighter than a threshold is sorted by
brightness along its row or column, so the picture smears into hard-edged
streaks while its dark shapes stay put; lowering the threshold lets the
streaks take more of the frame."""
import random
from contextlib import contextmanager

import cairo
from PIL import Image, ImageChops

import videobuilder as vb
from videobuilder.looks.fx import image_surface, surface_image

from .. import _demo as demo
from ..schema import Technique


def pixel_sort(im, threshold=0.5, vertical=False, reverse=False):
    """`im` (a PIL image) as RGB with each unbroken run of pixels at least
    `threshold` bright (0 -> 1) sorted by brightness, darkest first
    (`reverse`: brightest first). Runs follow rows, or columns when
    `vertical`. Above 1 nothing is sorted; at 0 every line is one ramp."""
    im = im.convert('RGB')
    if vertical:
        im = im.transpose(Image.Transpose.TRANSPOSE)
    w, h = im.size
    level = threshold * 255
    rgb, lum = im.tobytes(), im.convert('L').tobytes()
    out = bytearray(rgb)
    for row in range(0, w * h, w):
        x, stop = row, row + w
        while x < stop:
            if lum[x] < level:
                x += 1
                continue
            end = x + 1
            while end < stop and lum[end] >= level:
                end += 1
            if end - x > 1:
                at = x * 3
                for i in sorted(range(x, end), key=lum.__getitem__, reverse=reverse):
                    out[at:at + 3] = rgb[i * 3:i * 3 + 3]
                    at += 3
            x = end
    im = Image.frombytes('RGB', (w, h), bytes(out))
    return im.transpose(Image.Transpose.TRANSPOSE) if vertical else im


@contextmanager
def pixel_sorted(cv, threshold, box=None, vertical=False, reverse=False):
    """Everything drawn inside the block, within `box` (x, y, w, h in film
    px; default the whole frame), comes out pixel-sorted by `pixel_sort`
    with these options. Animate `threshold` from above 1 down to sweep the
    effect in. The pixels are sorted at the canvas's device size, so the
    streaks stay one device pixel wide at any preview scale."""
    yield cv
    if threshold > 1:
        return
    s = cv.scale
    x, y, w, h = box or (0, 0, cv.width, cv.height)
    sw, sh = cv.surface.get_width(), cv.surface.get_height()
    x0, y0 = max(0, round(x * s)), max(0, round(y * s))
    x1, y1 = min(sw, round((x + w) * s)), min(sh, round((y + h) * s))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    im = pixel_sort(surface_image(cv.surface, x0, y0, x1 - x0, y1 - y0), threshold, vertical, reverse)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_operator(cairo.OPERATOR_SOURCE)
    c.set_source_surface(image_surface(im), x0, y0)
    c.rectangle(x0, y0, x1 - x0, y1 - y0)
    c.fill()
    c.restore()


_SUBJECT = []


def subject():
    """The demo's picture: the kit photo with mottled and fine grain, so the
    bright runs break at uneven places and the sorted streaks show."""
    if not _SUBJECT:
        photo = demo.photo()
        w, h = photo.w, photo.h
        flat = vb.Canvas(w, h)
        flat.image(photo, 0, 0, w, h)
        base = surface_image(flat.surface)
        rnd = random.Random(5)
        noise = lambda nw, nh: Image.frombytes('L', (nw, nh), rnd.randbytes(nw * nh))  # noqa: E731
        mottle = noise(w // 8, h // 8).resize((w, h), Image.BICUBIC)
        tone = Image.blend(mottle, noise(w, h), 0.35)
        tone = Image.blend(Image.new('L', (w, h), 128), tone, 0.45).convert('RGB')
        pil = ImageChops.overlay(base, tone)
        _SUBJECT.append(vb.Image.from_pil(pil))
    return _SUBJECT[0]


def draw(n, cv):
    # the threshold falls from clean to deep, then eases partly back
    down = vb.ease_in_out_quart(demo.phase(n, 0.4, 1.9))
    back = vb.ease_in_out_quart(demo.phase(n, 2.3, 2.9))
    threshold = 1.02 - 0.76 * down + 0.3 * back
    img = subject()
    with pixel_sorted(cv, threshold, vertical=True):
        cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.mark('photo', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='pixel-sorting',
    name='Pixel sorting',
    family='vfx',
    group='Glitch',
    aliases=('pixel sort', 'pixel sort glitch', 'sorted pixels', 'databending streaks'),
    definition='Bright stretches of an image are reordered by brightness along each row or column, '
               'melting the picture into straight, smeared streaks while its darker shapes hold.',
    phrasings=('make the photo melt into glitchy streaks of colour',
               'that glitch where the pixels drip down in sorted bands',
               'smear the bright parts of the frame into long sorted lines'),
    related=('pixel-sort-text', 'pixelation', 'pixelate-transition', 'nearest-neighbor-upscale',
             'pixelation-reveal', 'pixel-build'),
    api=('videobuilder.techniques.vfx.pixel_sorting.pixel_sorted',
         'videobuilder.techniques.vfx.pixel_sorting.pixel_sort'),
    demo=lambda: demo.film(draw),
)

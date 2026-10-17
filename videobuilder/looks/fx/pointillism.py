"""Pointillism filter: the picture rebuilt from seeded dots of its own
colours on a pale ground. Each dot takes the colour under it, nudged warmer
or cooler for good, and every dot circles a little and shimmers towards a
neighbouring tone, so the whole surface swims even on a still picture.

Options: `pitch` -- px between dots at 1080 (14)."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image, ImageEnhance, ImageFilter

from . import Filter, image_surface, surface_image

GROUND = (246, 240, 226)


@lru_cache(maxsize=4)
def _dots(w, h, pitch):
    """The seeded dots for a w x h frame: (x, y, cell x, cell y, radius,
    phase, warm/cool shift), on a jittered grid, two passes so they overlap."""
    rnd = random.Random(7)
    cols, rows = max(1, math.ceil(w / pitch)), max(1, math.ceil(h / pitch))
    out = []
    for layer, size in ((0, 0.62), (1, 0.48)):
        off = 0.5 * pitch * layer
        for gy in range(rows):
            for gx in range(cols):
                x = gx * pitch + off + rnd.uniform(-0.35, 0.35) * pitch
                y = gy * pitch + off + rnd.uniform(-0.35, 0.35) * pitch
                cx, cy = min(cols - 1, max(0, int(x / pitch))), min(rows - 1, max(0, int(y / pitch)))
                out.append((x, y, cx, cy, size * pitch * rnd.uniform(0.85, 1.15), rnd.uniform(0, 2 * math.pi),
                            rnd.uniform(-1, 1)))
    rnd.shuffle(out)
    return tuple(out), cols, rows


def treat(im, t, age, u, pitch=14):
    w, h = im.size
    p = max(3.0, pitch * u)
    dots, cols, rows = _dots(w, h, round(p, 2))
    colours = ImageEnhance.Color(im.resize((cols, rows), Image.BOX)).enhance(1.35)
    data = colours.tobytes()
    ground = Image.blend(im.resize((max(1, w // 8), max(1, h // 8)), Image.BOX)
                         .filter(ImageFilter.GaussianBlur(2)).resize((w, h), Image.BILINEAR),
                         Image.new('RGB', (w, h), GROUND), 0.45)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    c = cairo.Context(surf)
    c.set_source_surface(image_surface(ground), 0, 0)
    c.paint()
    orbit = 0.18 * p
    for x, y, cx, cy, r, ph, shift in dots:
        i = 3 * (cy * cols + cx)
        s = 0.11 * shift + 0.09 * math.sin(t * 3.1 + ph)         # warm/cool, shimmering
        c.set_source_rgb(min(1.0, data[i] / 255 + s), data[i + 1] / 255 + 0.3 * s * s,
                         max(0.0, data[i + 2] / 255 - s))
        a = t * 1.7 + ph
        c.arc(x + orbit * math.cos(a), y + orbit * math.sin(a), r, 0, 2 * math.pi)
        c.fill()
    return surface_image(surf)


FILTER = Filter('pointillism', 'Pointillism filter', 'rebuilt from shimmering dots of its own colours', treat)

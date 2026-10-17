"""Woodblock filter: the picture cut into a few flat ink colours -- indigo,
Prussian blue, vermilion, ochre, sage -- on a cream paper, with every strong
edge inked in a thick line. The paper's grain and the ink lines boil on
twos (a new hand-printed impression every 1/15 s), so a held picture still
breathes like a print."""
import random

from PIL import Image, ImageChops, ImageFilter

from . import Filter, boil, edges, grow, luma, noise, palette_image, posterize, shrink, work_factor

INK = '#1c1a22'
PAPER = '#efe2c4'
COLOURS = (PAPER, '#e4c9a0', '#d8a040', '#c8402f', '#8a3a2a', '#7a8a5a', '#9ab8c8', '#3a6a8a', '#1d3a63', INK)
_PALETTE = palette_image(COLOURS)
IMPRESSIONS = 4    # paper textures the print boils between


def _paper(w, h, i):
    """Impression `i`'s paper: fine grain plus long horizontal wood fibres,
    grey about 128 (soft-light: lighter and darker than the ink it lands on)."""
    fine = noise(w, h, 100 + i, blur=0.5)
    fibres = noise(w, h, 200 + i, stretch=24, blur=0.8)
    g = Image.blend(fine, fibres, 0.4).point(lambda v: max(0, min(255, 128 + (v - 128) * 1.3)))
    return Image.merge('RGB', (g, g, g))


def treat(im, t, age, u):
    k = work_factor(u)
    small = shrink(im, k).filter(ImageFilter.MedianFilter(3))
    q = posterize(small, _PALETTE).filter(ImageFilter.ModeFilter(3))    # flat areas, no specks
    flat = grow(q.convert('RGB'), im.size)
    step = boil(t)
    rnd = random.Random(step)
    lines = grow(edges(luma(small), level=30, blur=1.0, thick=6 * u / k), im.size)
    lines = ImageChops.offset(lines, rnd.choice((-1, 0, 1)) * max(1, k), rnd.choice((-1, 0, 1)) * max(1, k))
    flat.paste(INK, (0, 0, *im.size), lines)
    w, h = im.size
    return ImageChops.soft_light(flat, _paper(w, h, rnd.randrange(IMPRESSIONS)))


FILTER = Filter('woodblock', 'Woodblock filter', 'flat inks, inked edges, paper that boils on twos', treat)

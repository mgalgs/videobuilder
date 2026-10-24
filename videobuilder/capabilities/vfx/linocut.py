"""Linocut: the same idea as Woodblock filter (`look_filter_woodblock.py`),
which keeps the capability -- both restyle any picture as a carved
black-and-paper block print: the picture cut to two inks -- solid black
and bare paper -- with the mid-tones carved out of the black as rough
horizontal gouge strokes (more of them where the picture is lighter), the
outline of every shape cut as a line in the opposite ink, and ragged
edges everywhere. The gouges boil on twos, so a held picture still reads
as a hand-pulled print. This module's own code stays (a film may still
import it), but it is no longer a capability of its own.

`LINOCUT` is a filter look (see `looks/fx`), applied with `linocut(cv, t)`
around whatever the film draws; the demo reveals the cut frame across the
photo behind a moving edge."""
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageFilter, ImageOps

import videobuilder as vb

from ...looks.fx import Filter, apply, boil, edges, grow, luma, noise, shrink, threshold, work_factor
from .. import _demo as demo

MERGED_INTO = 'look-filter-woodblock'

INK = '#16141a'
PAPER = '#efe9dc'
IMPRESSIONS = 4    # gouge patterns the print boils between


@lru_cache(maxsize=8)
def _gouges(w, h, i, length, thick):
    """Impression `i`'s carving: coarse grey noise, one sample per `length`
    x `thick` px, smoothed up to full size and pushed hard about 128, so
    thresholding a tone against it leaves long thin strokes that taper at
    both ends rather than dither dots."""
    cw, ch = max(1, w // length + 2), max(1, h // thick + 2)
    g = noise(cw, ch, 300 + i).resize((w + length * 2, h + thick * 2), Image.BICUBIC)
    g = g.crop((length, thick, length + w, thick + h))
    return g.point(lambda v: max(0, min(255, 128 + (v - 128) * 2)))


def treat(im, t, age, u, level=128, carve=0.6, outline=True):
    """`im` as a two-ink linocut (a `Filter.treat`). `level`: the grey that
    splits ink from paper; `carve`: how far gouge strokes reach into the
    tones either side of it (0: a clean two-tone cut, 1: strokes across
    every tone but pure black and white); `outline`: cut shape outlines
    in the opposite ink."""
    k = work_factor(u)
    gray = luma(shrink(im, k)).filter(ImageFilter.GaussianBlur(1.2 * u / k + 0.3))
    w, h = gray.size
    rnd = random.Random(boil(t, 12))
    gouge = _gouges(w, h, rnd.randrange(IMPRESSIONS), max(4, round(80 * u / k)), max(2, round(7 * u / k)))
    tone = ImageOps.equalize(gray)    # every shade gets its own share of carving, darks included
    # paper wherever tone - level > (128 - gouge) * carve: the gouges are a stroke-shaped threshold,
    # so lighter tones break up into more and longer strokes of paper and darker ones close into solid ink
    reach = gouge.point(lambda v: max(0, min(255, round(128 + (v - 128) * carve))))
    paper = threshold(ImageChops.add(tone, reach, scale=2), (level + 128) // 2)
    if outline:
        lines = edges(tone, level=24, blur=0, thick=4 * u / k)
        rough = threshold(noise(w, h, 400 + rnd.randrange(IMPRESSIONS), blur=0.6), 60)
        lines = ImageChops.multiply(lines, rough)                     # a nicked, uneven cut
        light = threshold(tone, level)
        flip = ImageChops.multiply(lines, ImageChops.invert(light))   # in the black: cut to paper
        keep = ImageChops.multiply(lines, light)                      # on the paper: an ink line
        paper = ImageChops.subtract(ImageChops.lighter(paper, flip), keep)
    paper = paper.filter(ImageFilter.ModeFilter(3))                   # chip off single-pixel specks
    out = Image.new('RGB', (w, h), INK)
    out.paste(PAPER, (0, 0, w, h), paper)
    return grow(out, im.size, Image.BILINEAR if k > 1 else Image.NEAREST)


LINOCUT = Filter('linocut', 'Linocut filter', 'two inks, carved gouge strokes, ragged cut edges', treat,
                 aliases=('woodcut', 'block print', 'relief print'))


def linocut(cv, t, age=None, box=None, **opts):
    """A context manager: everything drawn on `cv` inside it (and what was
    there already) comes out as a linocut print when the block ends -- the
    whole frame, or only `box` (x, y, w, h). `t` drives the gouges' boil;
    `opts` go to `treat` (`level=`, `carve=`, `outline=`)."""
    return apply(cv, LINOCUT, t, age, box, opts)


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    edge = demo.W * vb.ease_in_out_quart(demo.phase(n, 0.4, 2.2))    # the print slides in over the photo
    if edge >= 2:
        with cv.clip(0, 0, edge, demo.H), linocut(cv, n / demo.FPS):    # the whole frame cut, shown up to the edge
            pass
    if 0 < edge < demo.W:
        cv.rect(edge - 3, 0, 6, demo.H, demo.ACCENT)

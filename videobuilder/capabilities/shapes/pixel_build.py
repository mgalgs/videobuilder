"""Pixel Build: a picture assembles itself out of square pixels, each block
popping into its place on a grid until the whole image is there."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

HEART = ('..XXX...XXX..',
         '.XXOXX.XXXXX.',
         'XXOOXXXXXXXXX',
         'XXOXXXXXXXXXX',
         'XXXXXXXXXXXXX',
         '.XXXXXXXXXXX.',
         '..XXXXXXXXX..',
         '...XXXXXXX...',
         '....XXXXX....',
         '.....XXX.....',
         '......X......')


def build_order(rows, seed=0, sweep=0.6):
    """Each filled cell of `rows` (strings; any character but `.` or a space
    is a pixel) as `(col, row, char, start)`, `start` in [0, 1) saying when
    it arrives. `sweep` blends a bottom-to-top build (1) with pure random
    order (0); the same `seed` gives the same order."""
    rng = random.Random(seed)
    cells = [(c, r, ch) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch not in '. ']
    last = max(len(rows) - 1, 1)
    keyed = sorted(cells, key=lambda cell: sweep * (1 - cell[1] / last) + (1 - sweep) * rng.random())
    return [(c, r, ch, i / len(keyed)) for i, (c, r, ch) in enumerate(keyed)]


def pixel_build(cv, rows, x, y, size, p, colors, seed=0, sweep=0.6, pop=0.25, drop=0.6, gap=0.08):
    """Draw the pixel image `rows` with its top-left at (x, y), cells `size`
    apart, built up to progress `p` (0 -> 1). `colors` maps each character to
    a colour (or is one colour for all). Each pixel takes `pop` of the build
    to arrive: it scales up from nothing with a slight overshoot while
    falling `drop` cells into place. `gap` is the gutter between cells, as a
    fraction of `size`. Returns the Box of the whole image."""
    side = size * (1 - gap)
    for c, r, ch, start in build_order(rows, seed, sweep):
        q = vb.clamp01((p - start * (1 - pop)) / pop)
        if q <= 0:
            continue
        s = side * max(0.0, vb.ease_out_back(q))
        cx = x + (c + 0.5) * size
        cy = y + (r + 0.5) * size - drop * size * (1 - vb.ease_out_expo(q))
        color = colors if isinstance(colors, str) else colors[ch]
        cv.rect(cx - s / 2, cy - s / 2, s, s, color, radius=side * 0.12, alpha=min(1.0, q * 3))
    return vb.Box(x, y, max(len(line) for line in rows) * size, len(rows) * size)


def draw(n, cv):
    # fit the heart to the frame with clear margin, so the finished picture
    # and the top row falling into place both stay on screen
    size = min(demo.W * 0.6 / len(HEART[0]), demo.H * 0.75 / len(HEART))
    w, h = len(HEART[0]) * size, len(HEART) * size
    box = pixel_build(cv, HEART, (demo.W - w) / 2, (demo.H - h) / 2, size, demo.phase(n, 0.3, 2.4),
                      {'X': demo.ACCENT, 'O': demo.INK}, seed=3)
    cv.mark('image', *box)


CAPABILITY = Capability(
    id='pixel-build',
    name='Pixel build',
    family='shapes',
    group='Bursts & particles',
    aliases=('pixel assemble', 'block build', 'pixel art build-up'),
    definition='An image is put together from small square blocks that pop onto a grid one after another, '
               'filling in until the full pixel picture stands complete.',
    phrasings=('build the icon up out of little square pixels',
               'have the logo assemble block by block like pixel art',
               'squares pop in one at a time until the picture is finished'),
    related=('pixelate-transition', 'pixelation', 'pixelation-reveal', 'pixel-sort-text', 'pixel-sorting',
             'image-to-particles'),
    api=('videobuilder.capabilities.shapes.pixel_build.pixel_build',
         'videobuilder.capabilities.shapes.pixel_build.build_order'),
    demo=lambda: demo.film(draw),
)

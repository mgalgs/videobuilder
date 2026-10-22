"""Lenia: a cellular automaton with smooth states, a ring-shaped neighbourhood
and a bell-shaped growth rule, in which soft blobs hold together and glide
like small creatures.

The field is a flat row-major list of floats in 0..1 on a torus. One step
weighs every cell's ring of neighbours (`lenia_kernel`), turns that into
growth or decay through a bell around `mu`, and nudges the cell by `dt`.
Pure Python, so keep grids small (about 100 x 60 at radius 9 runs a step in
well under a tenth of a second) and upscale when drawing: `draw_lenia`
smooths the field into a soft image the size of any box."""
import math
from functools import lru_cache
from operator import add

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# One glider grown from noise at radius 9, mu 0.15, sigma 0.015, dt 0.1: two
# hex digits per cell (00 -> 0, ff -> 1). Unturned it drifts left and down,
# about 0.42 cells a step.
GLIDER = (
    '0000000000000054000000000000',
    '0000000000d63722120000000000',
    '0000004e8000000f292700000000',
    '00004c1300000000002956200000',
    '00380f000000000026346e280000',
    '06330200002fa18a5d1a52630d00',
    '1838234ed2fbdd793d4a2d2e0b00',
    '1e516fc7e9c8c2c38e2e00270f00',
    '155b8ab2a8b9ffc8120000220f00',
    '07487ca0c1febc000000002c004b',
    '00225d848b570000000007820000',
    '00022d584f1800000019cf000000',
    '0000001e3e3a2c386d0000000000',
    '0000000000060800000000000000',
)


@lru_cache(maxsize=8)
def lenia_kernel(radius=9):
    """The ring of neighbours at `radius` cells: a tuple of `(weight, offsets)`,
    one per distance, the weights a smooth bump peaking halfway out and
    summing to 1 over every offset."""
    rings = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            r = math.hypot(dx, dy) / radius
            if 0 < r < 1:
                w = math.exp(4 - 1 / (r * (1 - r)))
                if w > 1e-4:
                    rings.setdefault(dx * dx + dy * dy, [w, []])[1].append((dx, dy))
    total = sum(w * len(offs) for w, offs in rings.values())
    return tuple((w / total, tuple(offs)) for w, offs in rings.values())


def lenia_step(field, width, height, radius=9, mu=0.15, sigma=0.015, dt=0.1):
    """One Lenia step of `field` (`width * height` floats, row-major, wrapping
    at the edges): each cell grows where its ring's weighted average sits near
    `mu` (within about `sigma`) and fades elsewhere, by up to `dt`. Returns a
    new list."""
    pw = width + 2 * radius
    padded = []
    for y in range(-radius, height + radius):
        row = field[(y % height) * width:(y % height + 1) * width]
        padded.extend(row[width - radius:] + row + row[:radius])
    n = height * pw
    near = None
    for w, offs in lenia_kernel(radius):
        # every offset of one distance at once: a shifted slice of the padded field each
        rings = (padded[o:o + n] for o in ((radius + dy) * pw + radius + dx for dx, dy in offs))
        part = map(w.__mul__, map(sum, zip(*rings)))
        near = list(part) if near is None else list(map(add, near, part))
    k, exp, out = 1 / (2 * sigma * sigma), math.exp, []
    for y in range(height):
        for u, a in zip(near[y * pw:y * pw + width], field[y * width:(y + 1) * width]):
            v = a + dt * (2 * exp(-(u - mu) ** 2 * k) - 1)
            out.append(0.0 if v < 0 else 1.0 if v > 1 else v)
    return out


def place(field, width, height, x, y, pattern=GLIDER, turn=0, mirror=False):
    """Stamp `pattern` (rows of two-digit hex cells, like `GLIDER`) into
    `field` in place, centred on cell (x, y), wrapping at the edges. `turn`
    rotates it by quarter turns clockwise and `mirror` flips it left to right
    first, which for `GLIDER` picks one of eight headings."""
    cells = [[int(row[i:i + 2], 16) / 255 for i in range(0, len(row), 2)] for row in pattern]
    if mirror:
        cells = [row[::-1] for row in cells]
    for _ in range(turn % 4):
        cells = [list(r) for r in zip(*cells[::-1])]
    h, w = len(cells), len(cells[0])
    for j, row in enumerate(cells):
        for i, v in enumerate(row):
            if v:
                field[((y - h // 2 + j) % height) * width + (x - w // 2 + i) % width] = v
    return field


def lenia_image(field, width, height, colors=(demo.BG, demo.TEAL, demo.INK), smooth=4):
    """`field` as a `vb.Image`: upscaled `smooth` times with a soft filter,
    then coloured along `colors` (0 -> the first, 1 -> the last)."""
    grey = PILImage.frombytes('L', (width, height), bytes(round(v * 255) for v in field))
    grey = grey.resize((width * smooth, height * smooth), PILImage.BICUBIC)
    stops = [vb.rgba(c)[:3] for c in colors]
    lut = []
    for ch in range(3):
        for i in range(256):
            t = i / 255 * (len(stops) - 1)
            k = min(int(t), len(stops) - 2)
            lut.append(round(255 * (stops[k][ch] + (stops[k + 1][ch] - stops[k][ch]) * (t - k))))
    return vb.Image.from_pil(grey.convert('RGB').point(lut))


def draw_lenia(cv, field, width, height, x, y, w, h, colors=(demo.BG, demo.TEAL, demo.INK), alpha=1.0):
    """Draw `field` filling the box (x, y, w, h), coloured as in `lenia_image`."""
    cv.image(lenia_image(field, width, height, colors), x, y, w, h, alpha=alpha)


GW, GH = 112, 63
SEEDS = ((10, 52, 2, False), (66, 52, 2, False), (38, 28, 2, True), (94, 28, 2, True))  # two lanes rising past each other


@lru_cache(maxsize=1)
def _states():
    field = [0.0] * (GW * GH)
    for x, y, turn, mirror in SEEDS:
        place(field, GW, GH, x, y, turn=turn, mirror=mirror)
    states = [field]
    for _ in range(round(demo.SECONDS * demo.FPS) - 1):
        states.append(lenia_step(states[-1], GW, GH))
    return states


def draw(n, cv):
    draw_lenia(cv, _states()[n], GW, GH, 0, 0, demo.W, demo.H,
               colors=(demo.BG, '#173a44', demo.TEAL, '#f2d7a0', demo.INK))


CAPABILITY = Capability(
    id='lenia',
    name='Lenia',
    family='particles',
    group='Cellular automata',
    aliases=('continuous game of life', 'smooth life', 'lenia creatures', 'orbium'),
    definition='Soft glowing blobs on a grid of smoothly varying cells that hold their shape and glide '
               'about like tiny organisms, each cell growing or fading by how full the ring around it is.',
    phrasings=('little soft creatures swimming around like a game of life but smooth',
               'blurry cellular automaton blobs that crawl across the screen',
               'organic glowing cells that move like microscopic life'),
    related=('eden-growth', 'voronoi-relaxation', 'morphing-blob', 'differential-growth',
             'diffusion-limited-aggregation', 'hopalong-attractor'),
    api=('videobuilder.capabilities.particles.lenia.lenia_step',
         'videobuilder.capabilities.particles.lenia.place',
         'videobuilder.capabilities.particles.lenia.draw_lenia',
         'videobuilder.capabilities.particles.lenia.lenia_image',
         'videobuilder.capabilities.particles.lenia.lenia_kernel',
         'videobuilder.capabilities.particles.lenia.GLIDER'),
    demo=lambda: demo.film(draw),
)

"""Fractal Brownian Motion: layers ("octaves") of smooth noise are stacked,
each finer and fainter than the one before, so a soft blur of blobs gains
billows, then wisps, then grain -- cloud, smoke or terrain with detail at
every scale. Drifting the layers makes it roll like weather."""
import math
import random
from functools import lru_cache

from PIL import Image, ImageOps

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@lru_cache(maxsize=64)
def _lattice(cells, seed, k):
    """The random grey lattice of octave `k`: `cells` x `cells` values that
    wrap, tiled 3 x 3 with a border so a bicubic read around the middle tile,
    turned and offset, never runs off the edge."""
    rnd = random.Random(f'fbm:{seed}:{k}')
    tile = Image.frombytes('L', (cells, cells), rnd.randbytes(cells * cells))
    out = Image.new('L', (3 * cells + 4, 3 * cells + 4))
    for i in range(-1, 4):
        for j in range(-1, 4):
            out.paste(tile, (2 + i * cells, 2 + j * cells))
    return out


def octave(w, h, k, seed=0, scale=3.0, lacunarity=2.0, drift=(0.0, 0.0)):
    """One octave of the stack as a w x h grey image: smooth value noise with
    `scale * lacunarity ** k` features across the width, slid by `drift`
    (in base-octave units, so every octave moves together like one sheet).
    Each octave is turned to its own angle so the lattices never line up."""
    freq = scale * lacunarity ** k
    cells = max(2, math.ceil(1.5 * freq * max(1.0, h / w)) + 1)
    rnd = random.Random(f'fbm-shift:{seed}:{k}')
    a = rnd.uniform(0, 2 * math.pi)
    ox = (drift[0] * lacunarity ** k + rnd.uniform(0, cells)) % cells
    oy = (drift[1] * lacunarity ** k + rnd.uniform(0, cells)) % cells
    step = freq / w  # lattice cells per pixel
    c, s = step * math.cos(a), step * math.sin(a)
    cx, cy = 2 + cells + ox, 2 + cells + oy  # where the image centre reads from
    return _lattice(cells, seed, k).transform(
        (w, h), Image.AFFINE, (c, -s, cx - c * w / 2 + s * h / 2, s, c, cy - s * w / 2 - c * h / 2),
        Image.BICUBIC)


def fbm(w, h, octaves=6, seed=0, scale=3.0, lacunarity=2.0, gain=0.5, drift=(0.0, 0.0), contrast=2.2):
    """Fractal Brownian motion as a w x h grey `PIL.Image` ('L'): `octaves`
    layers of value noise, each `lacunarity` times finer and `gain` times
    fainter, averaged by weight. `octaves` may be fractional -- the last layer
    fades in by the fraction -- so it can be animated from smooth to detailed.
    `drift` (x, y) slides the whole field, in base-feature units; animate it
    for rolling clouds. `contrast` stretches the grey about mid so the sum
    (which flattens as layers average out) keeps its darks and lights."""
    octaves = max(1.0, float(octaves))
    out, total = None, 0.0
    for k in range(math.ceil(octaves)):
        amp = gain ** k * min(1.0, octaves - k)
        if amp <= 0:
            break
        layer = octave(w, h, k, seed, scale, lacunarity, drift)
        total += amp
        out = layer if out is None else Image.blend(out, layer, amp / total)
    return out.point(lambda v: max(0, min(255, round(128 + (v - 128) * contrast))))


def fbm_image(w, h, low=demo.BG, mid=demo.TEAL, high=demo.INK, **kw):
    """`fbm(w, h, **kw)` coloured through a three-stop ramp (`low` for the
    valleys, `high` for the peaks) and wrapped as a `vb.Image` ready for
    `cv.image`."""
    return vb.Image.from_pil(ImageOps.colorize(fbm(w, h, **kw), low, high, mid))


MAX_OCTAVES = 7
RES = 300       # field pixels per side; drawn up to the panel
PANEL = 400


def _count(n):
    """The octave count at frame `n`: 1 at the start, climbing to MAX_OCTAVES."""
    p = demo.phase(n, 0.35, 2.55)
    return 1 + (MAX_OCTAVES - 1) * p


def draw(n, cv):
    t = n / demo.FPS
    count = _count(n)
    drift = (0.22 * t, 0.08 * t)
    x, y = 90, (demo.H - PANEL) / 2
    img = fbm_image(RES, RES, octaves=count, seed=4, scale=2.6, drift=drift)
    cv.shadow(x, y, PANEL, PANEL, radius=16, dy=8, blur=24, color=(0, 0, 0, 0.45))
    with cv.clip(x, y, PANEL, PANEL, radius=16):
        cv.image(img, x, y, PANEL, PANEL)
    cv.mark('field', x, y, PANEL, PANEL)

    # the stack: one chip per octave (finer each row), lit as it joins, its bar showing its weight
    lx, chip, gap = x + PANEL + 80, 42, 8
    label = '1 octave' if count < 2 else f'{min(MAX_OCTAVES, int(count))} octaves'
    vb.text.draw(cv, [label], demo.font(30, 800), lx, y, demo.INK)
    for k in range(MAX_OCTAVES):
        on = vb.clamp01(count - k)
        cy = y + 58 + k * (chip + gap)
        layer = octave(2 * chip, 2 * chip, k, seed=4, scale=1.3, drift=drift)
        layer = vb.Image.from_pil(ImageOps.colorize(layer, demo.BG, demo.INK, demo.TEAL))
        with cv.clip(lx, cy, chip, chip, radius=8):
            cv.image(layer, lx, cy, chip, chip, alpha=0.15 + 0.85 * on)
        cv.rect(lx + chip + 18, cy + chip / 2 - 7, 220 * 0.5 ** k + 6, 14, demo.TEAL, radius=7,
                alpha=0.15 + 0.85 * on)


TECHNIQUE = Technique(
    id='fractal-brownian-motion',
    name='Fractal Brownian motion',
    family='particles',
    group='Noise & fields',
    aliases=('fBm', 'fbm noise', 'layered octaves noise', 'fractal noise', 'octave noise'),
    definition='Copies of smooth noise at ever finer sizes and ever weaker strengths are stacked together, '
               'turning soft blobs into cloudy, craggy texture with detail at every scale.',
    phrasings=('make a rolling cloud texture out of noise',
               'stack a few layers of noise so it gets more detailed and natural looking',
               'give me smoky, terrain-like noise instead of plain soft blobs'),
    related=('static-noise', 'noise-vertex-wobble', 'turbulence-displacement', 'floyd-steinberg-dithering',
             'perlin-noise-drift', 'burning-ship-fractal'),
    api=('videobuilder.techniques.particles.fractal_brownian_motion.fbm',
         'videobuilder.techniques.particles.fractal_brownian_motion.fbm_image',
         'videobuilder.techniques.particles.fractal_brownian_motion.octave'),
    demo=lambda: demo.film(draw),
)

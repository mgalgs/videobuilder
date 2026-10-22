"""Perlin Noise Field: a smooth, endlessly varied random pattern -- soft
blobs of light and dark with no hard edges -- painted across an area and
slowly churning in place, like clouds or lava seen from above."""
import math
import random
from functools import lru_cache

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba

# Gradients at the corners of each lattice cube: the twelve cube-edge midpoints.
_GRADS = ((1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0), (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
          (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1))


@lru_cache(maxsize=16)
def _perm(seed):
    p = list(range(256))
    random.Random(f'perlin-field:{seed}').shuffle(p)
    return tuple(p * 2)


def _fade(f):
    return f * f * f * (f * (f * 6 - 15) + 10)


def perlin3(x, y, z, seed=0):
    """3-D Perlin (gradient) noise at (x, y, z), smooth and roughly in
    [-1, 1], with features about one unit across. Use z as time to have a
    2-D slice through it churn in place rather than slide."""
    p = _perm(seed)
    x0, y0, z0 = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - x0, y - y0, z - z0
    X, Y, Z = x0 & 255, y0 & 255, z0 & 255
    u, v, w = _fade(fx), _fade(fy), _fade(fz)

    def corner(i, j, k):
        gx, gy, gz = _GRADS[p[p[p[X + i] + Y + j] + Z + k] % 12]
        return gx * (fx - i) + gy * (fy - j) + gz * (fz - k)

    def lerp(a, b, s):
        return a + s * (b - a)

    return lerp(lerp(lerp(corner(0, 0, 0), corner(1, 0, 0), u), lerp(corner(0, 1, 0), corner(1, 1, 0), u), v),
                lerp(lerp(corner(0, 0, 1), corner(1, 0, 1), u), lerp(corner(0, 1, 1), corner(1, 1, 1), u), v), w)


def field_value(x, y, t, seed=0, size=120.0, speed=0.45, octaves=2, contrast=2.4):
    """The field's level, 0 -> 1, at point (x, y) (px) and time `t`
    seconds: `octaves` layers of Perlin noise with blobs about `size` px
    across, each layer twice as fine and half as strong, evolving at
    `speed` (noise units a second). `contrast` stretches the mid-greys
    toward the ends so the blobs read as light and dark, not mush."""
    total, amp, norm = 0.0, 1.0, 0.0
    for i in range(octaves):
        f = 2 ** i
        total += amp * perlin3(x / size * f + 13.1 * i, y / size * f - 7.7 * i, t * speed * f, seed)
        norm += amp
        amp *= 0.5
    return vb.clamp01(0.5 + 0.5 * contrast * total / norm)


def _ramp(colors):
    stops = [rgba(c)[:3] for c in colors]
    out = []
    for k in range(256):
        s = k / 255 * (len(stops) - 1)
        i = min(int(s), len(stops) - 2)
        f = s - i
        out.append(tuple(round(255 * (a + f * (b - a))) for a, b in zip(stops[i], stops[i + 1])))
    return out


def draw_noise_field(cv, x, y, w, h, t, colors=('#0b0c10', '#1f5f57', demo.TEAL, '#e4f7f3'), seed=0,
                     size=120.0, speed=0.45, octaves=2, contrast=2.4, cell=7, radius=0, alpha=1.0):
    """Paint an animated Perlin noise field into the box (x, y, w, h) at
    time `t` seconds: the field (see `field_value`) mapped through the
    gradient `colors` (low -> high), clipped to a rounded box of `radius`.
    The field is sampled every `cell` px and smoothly upscaled, so keep
    `cell` well under `size`. Animate `t` for a field that churns; draw it
    full-frame for a living backdrop or in a panel as a texture."""
    cols, rows = max(2, round(w / cell) + 1), max(2, round(h / cell) + 1)
    lut = _ramp(colors)
    px = []
    for j in range(rows):
        fy = y + h * j / (rows - 1)
        for i in range(cols):
            fx = x + w * i / (cols - 1)
            px.append(lut[round(255 * field_value(fx, fy, t, seed, size, speed, octaves, contrast))])
    small = Image.new('RGB', (cols, rows))
    small.putdata(px)
    s = cv.scale_factor()
    big = small.resize((max(1, round(w * s)), max(1, round(h * s))), Image.BICUBIC)
    with cv.clip(x, y, w, h, radius=radius):
        cv.image(vb.Image.from_pil(big), x, y, w, h, alpha=alpha)


def draw(n, cv):
    w, h = 780, 410
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cv.shadow(x, y, w, h, radius=18, dy=8, blur=24, color=(0, 0, 0, 0.5))
    draw_noise_field(cv, x, y, w, h, n / demo.FPS, seed=4, size=160, speed=0.45, cell=8, radius=18)
    cv.mark('field', x, y, w, h)


TECHNIQUE = Technique(
    id='perlin-noise-field',
    name='Perlin noise field',
    family='particles',
    group='Noise & fields',
    aliases=('gradient noise', 'Perlin noise texture', 'noise texture', 'cloud noise'),
    definition='An area is filled with soft, organic blotches of light and dark that blend smoothly into '
               'each other and slowly churn and reshape over time.',
    phrasings=('a moving cloudy noise texture as the background',
               'smooth random blobs that slowly shift like lava',
               'fill the panel with animated Perlin noise'),
    related=('perlin-noise-drift', 'gradient-mesh-drift', 'film-grain', 'turbulence-displacement',
             'noise-field-warp', 'gradient-wipe'),
    api=('videobuilder.techniques.particles.perlin_noise_field.draw_noise_field',
         'videobuilder.techniques.particles.perlin_noise_field.field_value',
         'videobuilder.techniques.particles.perlin_noise_field.perlin3'),
    demo=lambda: demo.film(draw),
)

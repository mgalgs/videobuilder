"""Domain Warping: a noise field looked up not at each point but at a point
that is itself pushed around by more noise, twice over, so plain cloudy
noise folds into marbled, smoke-like swirls that flow as time runs."""
import math
import random

from PIL import Image, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


class ValueNoise:
    """Seeded 2-D value noise with smooth interpolation, in [0, 1]."""

    def __init__(self, seed=0):
        rnd = random.Random(seed)
        self.perm = [rnd.randrange(256) for _ in range(256)] * 2
        self.vals = [rnd.random() for _ in range(256)]

    def __call__(self, x, y):
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = x - x0, y - y0
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        p, v = self.perm, self.vals
        i, j = x0 & 255, y0 & 255
        a, b = p[i] + j, p[i + 1] + j
        n00, n01, n10, n11 = v[p[a]], v[p[a + 1]], v[p[b]], v[p[b + 1]]
        top = n00 + sx * (n10 - n00)
        bot = n01 + sx * (n11 - n01)
        return top + sy * (bot - top)

    def fbm(self, x, y, octaves=4):
        """`octaves` layers, each twice as fine and half as strong, in [0, 1]."""
        total, amp, norm = 0.0, 0.5, 0.0
        for _ in range(octaves):
            total += amp * self(x, y)
            norm += amp
            # Rotate a little between octaves so the grid never lines up.
            x, y = 1.6 * x + 1.2 * y + 5.2, -1.2 * x + 1.6 * y + 1.3
            amp *= 0.5
        return total / norm


_noises = {}


def _noise(seed):
    if seed not in _noises:
        _noises[seed] = ValueNoise(f'domain-warp:{seed}')
    return _noises[seed]


def domain_warp(u, v, t=0.0, amount=1.0, seed=0, octaves=4, speed=0.15):
    """The warped field at point (u, v), in noise units (one unit is one
    coarse blob), at time `t` seconds. Returns (f, q, r): `f` the final value
    in [0, 1]; `q` and `r` how far the first and second warps moved the
    lookup, each about [0, 1], handy for colouring the folds.

    f = fbm(p + 4 * amount * r), r = fbm2(p + 4 * amount * q), q = fbm2(p):
    `amount` 0 is plain fbm noise, 1 the full marbled fold."""
    n = _noise(seed)
    fbm = n.fbm
    d = t * speed
    k = 4.0 * amount
    qx = fbm(u + d, v, octaves) - 0.5
    qy = fbm(u + 5.2, v + 1.3 - d, octaves) - 0.5
    rx = fbm(u + k * qx + 1.7 - 0.6 * d, v + k * qy + 9.2, octaves) - 0.5
    ry = fbm(u + k * qx + 8.3, v + k * qy + 2.8 + 0.5 * d, octaves) - 0.5
    f = fbm(u + k * rx, v + k * ry, octaves)
    return f, min(1.0, 2 * math.hypot(qx, qy)), min(1.0, 2 * math.hypot(rx, ry))


PALETTE = ('#0b1a2e', '#1f6f78', '#e9b872', '#f4efe3')  # deep, folds, glow, highlight


def _rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, s):
    return tuple(x + (y - x) * s for x, y in zip(a, b))


def domain_warp_image(cols, rows, t=0.0, amount=1.0, seed=0, scale=3.0, octaves=4, speed=0.15,
                      palette=PALETTE):
    """A PIL RGB image `cols` x `rows` of the warped field, `scale` noise
    units across its width, coloured through `palette` (dark, fold, glow,
    highlight). Keep it small and scale it up: the field is smooth."""
    deep, fold, glow, high = (_rgb(c) for c in palette)
    px = bytearray()
    for j in range(rows):
        v = scale * j / cols
        for i in range(cols):
            f, q, r = domain_warp(scale * i / cols, v, t, amount, seed, octaves, speed)
            s = max(0.0, min(1.0, (f - 0.25) * 2.0))
            c = _mix(deep, fold, s)
            c = _mix(c, glow, max(0.0, min(1.0, r * 1.4 - 0.2)) * s)
            c = _mix(c, high, max(0.0, min(1.0, (f - 0.62) * 4)) * (0.4 + 0.6 * q))
            px += bytes(max(0, min(255, round(x))) for x in c)
    return Image.frombytes('RGB', (cols, rows), bytes(px))


def draw_domain_warp(cv, x, y, w, h, t=0.0, amount=1.0, seed=0, scale=3.0, octaves=4, speed=0.15,
                     palette=PALETTE, detail=160):
    """Fill the region (x, y, w, h) of `cv` with the domain-warped field at
    time `t`. Animate `t` for the flow and `amount` (0 plain noise -> 1 full
    swirl) to fold it in or out. `detail`: field samples across the width at
    full size (fewer at preview scales); the image is smoothed up from there."""
    s = cv.scale_factor()
    cols = max(8, min(detail, round(w * s / 4)))
    rows = max(4, round(cols * h / w))
    im = domain_warp_image(cols, rows, t, amount, seed, scale, octaves, speed, palette)
    big = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(max(0.5, w * s / cols * 0.35)))
    cv.image(vb.Image.from_pil(big), x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    # Plain noise clouds first, then the warp folds in and keeps flowing.
    amount = 0.08 + 0.92 * vb.ease_in_out_quart(demo.phase(n, 0.4, 1.8))
    draw_domain_warp(cv, 0, 0, demo.W, demo.H, t=1.5 + 1.2 * t, amount=amount, seed=3)


TECHNIQUE = Technique(
    id='domain-warping',
    name='Domain warping',
    family='particles',
    group='Noise & fields',
    aliases=('warped noise', 'fbm warp', 'noise warping', 'marbled noise'),
    definition='A noise pattern is sampled at positions that further noise keeps shoving around, '
               'so soft clouds fold into flowing marble or smoke swirls.',
    phrasings=('a swirling marbled background like ink folding in water',
               'make the noise texture twist into flowing smoky curls',
               'an organic, liquid-looking abstract pattern that keeps moving'),
    related=('noise-field-warp', 'noise-vertex-wobble', 'swirl', 'turbulence-displacement',
             'refraction-ripple', 'film-grain'),
    api=('videobuilder.techniques.particles.domain_warping.draw_domain_warp',
         'videobuilder.techniques.particles.domain_warping.domain_warp_image',
         'videobuilder.techniques.particles.domain_warping.domain_warp'),
    demo=lambda: demo.film(draw),
)

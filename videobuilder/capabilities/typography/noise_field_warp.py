"""Noise Field Warp: whatever is drawn inside the warp -- usually a word -- is
pushed around by a smooth, slowly drifting noise field, so its strokes ripple
and pool like ink seen through moving water, then settle back to clean."""
import math
import random
from contextlib import contextmanager

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


class Noise:
    """Seeded 2-D gradient noise, smooth and roughly in [-1, 1]."""

    def __init__(self, seed=0):
        rnd = random.Random(seed)
        perm = list(range(256))
        rnd.shuffle(perm)
        self.perm = perm * 2
        self.grads = [(math.cos(a), math.sin(a)) for a in (rnd.uniform(0, 2 * math.pi) for _ in range(256))]

    def _dot(self, ix, iy, x, y):
        gx, gy = self.grads[self.perm[(self.perm[ix & 255] + iy) & 255]]
        return gx * (x - ix) + gy * (y - iy)

    def __call__(self, x, y):
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = x - x0, y - y0
        sx = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
        sy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
        a = self._dot(x0, y0, x, y) + sx * (self._dot(x0 + 1, y0, x, y) - self._dot(x0, y0, x, y))
        b = self._dot(x0, y0 + 1, x, y) + sx * (self._dot(x0 + 1, y0 + 1, x, y) - self._dot(x0, y0 + 1, x, y))
        return 1.4 * (a + sy * (b - a))

    def fbm(self, x, y, octaves=2):
        """`octaves` layers of noise, each twice as fine and half as strong."""
        total, amp, norm = 0.0, 1.0, 0.0
        for i in range(octaves):
            total += amp * self(x * 2 ** i + 17.3 * i, y * 2 ** i - 9.1 * i)
            norm += amp
            amp *= 0.5
        return total / norm


def field(x, y, t, seed=0, size=220.0, speed=0.35, octaves=2):
    """The displacement (dx, dy), each in about [-1, 1], at film point (x, y)
    and time `t` seconds: two noise layers of feature `size` px, drifting
    through the field at `speed` cells a second."""
    nx, ny = _noises(seed)
    u, v = x / size, y / size
    drift = t * speed
    return nx.fbm(u + drift, v - 0.6 * drift, octaves), ny.fbm(u - 0.7 * drift + 31.7, v + drift, octaves)


_cache = {}


def _noises(seed):
    if seed not in _cache:
        _cache[seed] = (Noise(f'{seed}:x'), Noise(f'{seed}:y'))
    return _cache[seed]


@contextmanager
def noise_warp(cv, x, y, w, h, amount, t, seed=0, size=220.0, speed=0.35, octaves=2, cell=16):
    """Draw into the yielded Canvas (same film coordinates as `cv`) and the
    region (x, y, w, h) comes back displaced by the noise `field` at time
    `t`, by up to about `amount` film px. Leave room around the content for
    the push: anything moved out of the region is cut off. `amount` 0 draws
    it untouched; animate `amount` for a warp that swells and settles, and
    `t` for the field's own flow. `cell` is the mesh spacing in film px."""
    s = cv.scale_factor()
    pw, ph = max(1, math.ceil(w * s)), max(1, math.ceil(h * s))
    sub = vb.Canvas(pw / s, ph / s, scale=s, format=cv.format)
    sub.ctx.translate(-x, -y)
    yield sub
    sub.surface.flush()
    src = sub.surface
    if amount:
        # Premultiplied BGRA straight through PIL as 'RGBA': bilinear sampling
        # of premultiplied pixels is the right blend, so no conversion either way.
        im = Image.frombuffer('RGBA', (pw, ph), bytes(src.get_data()), 'raw', 'RGBA', src.get_stride(), 1)
        cols, rows = max(1, round(w / cell)), max(1, round(h / cell))
        pts = [[None] * (cols + 1) for _ in range(rows + 1)]
        for j in range(rows + 1):
            for i in range(cols + 1):
                fx, fy = x + w * i / cols, y + h * j / rows
                dx, dy = field(fx, fy, t, seed, size, speed, octaves)
                # The mesh maps each output cell back to where it samples from.
                pts[j][i] = ((fx - x - dx * amount) * s, (fy - y - dy * amount) * s)
        mesh = []
        for j in range(rows):
            for i in range(cols):
                box = (round(pw * i / cols), round(ph * j / rows), round(pw * (i + 1) / cols),
                       round(ph * (j + 1) / rows))
                ul, ll, lr, ur = pts[j][i], pts[j + 1][i], pts[j + 1][i + 1], pts[j][i + 1]
                mesh.append((box, (*ul, *ll, *lr, *ur)))
        out = im.transform((pw, ph), Image.MESH, mesh, Image.BILINEAR)
        data = bytearray(out.tobytes('raw', 'RGBA'))
        src = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, pw, ph, pw * 4)
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(1 / s, 1 / s)
    c.set_source_surface(src, 0, 0)
    c.rectangle(0, 0, pw, ph)
    c.fill()
    c.restore()


def draw(n, cv):
    t = n / demo.FPS
    # Clean, swell into the warp, hold, settle back to clean.
    rise, fall = demo.phase(n, 0.3, 1.1), demo.phase(n, 2.0, 2.8)
    amount = 46 * vb.ease_in_out_quart(rise) * (1 - vb.ease_in_out_quart(fall))
    f = demo.font(230, 900)
    text = 'LIQUID'
    tw, th = vb.text.block_size([text], f)
    pad = 90
    x, y, w, h = (demo.W - tw) / 2 - pad, (demo.H - th) / 2 - pad, tw + 2 * pad, th + 2 * pad
    with noise_warp(cv, x, y, w, h, amount, t, seed=3, size=180, speed=0.5) as sub:
        box = demo.word(sub, text, demo.W / 2, demo.H / 2, size=230, color=demo.INK, weight=900)
        demo.word(sub, 'flowing through a noise field', demo.W / 2, box.y + box.h + 40, size=34,
                  color=demo.TEAL, weight=700)
    cv.mark('text', x, y, w, h)


TECHNIQUE = Technique(
    id='noise-field-warp',
    name='Noise field warp',
    family='typography',
    group='Liquid and organic',
    aliases=('noise displacement', 'liquid text', 'turbulent displace', 'perlin warp'),
    definition='Letters are pushed around by a smooth drifting noise pattern, so their strokes ripple '
               'and bulge like type under moving water before settling.',
    phrasings=('make the title wobble like it is underwater',
               'warp the text with a flowing, organic distortion',
               'the word melts and ripples, then snaps back to normal'),
    related=('domain-warping', 'noise-vertex-wobble', 'noise-dissolve', 'dot-grid-displacement',
             'turbulence-displacement', 'arc-bend-morph'),
    api=('videobuilder.techniques.typography.noise_field_warp.noise_warp',
         'videobuilder.techniques.typography.noise_field_warp.field',
         'videobuilder.techniques.typography.noise_field_warp.Noise'),
    demo=lambda: demo.film(draw),
)

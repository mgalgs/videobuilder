"""Clifford attractor: one point hopped again and again through a little sine
and cosine map lands, hop by hop, on a fixed swirling shape, and the hops
pile up into a glowing cloud of density."""
import math
from array import array
from functools import lru_cache

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

CLASSIC = (-1.4, 1.6, 1.0, 0.7)  # a, b, c, d: a well-known pair of curling lobes


def clifford_step(x, y, a, b, c, d):
    """One hop of the Clifford map from (x, y)."""
    return math.sin(a * y) + c * math.cos(a * x), math.sin(b * x) + d * math.cos(b * y)


def clifford_points(n, params=CLASSIC, start=(0.1, 0.1), skip=100):
    """The first `n` points of the orbit from `start` under `params`
    (a, b, c, d), after dropping `skip` warm-up hops. The cloud lies within
    |x| <= 1 + |c|, |y| <= 1 + |d|."""
    x, y = start
    out = []
    for i in range(n + skip):
        x, y = clifford_step(x, y, *params)
        if i >= skip:
            out.append((x, y))
    return out


@lru_cache(maxsize=8)
def _bins(n, params, gw, gh):
    """Each orbit point's cell in a gw x gh grid spanning the cloud's bounds."""
    rx, ry = 1 + abs(params[2]), 1 + abs(params[3])
    out = array('i')
    for x, y in clifford_points(n, params):
        i = min(gw - 1, int((x + rx) / (2 * rx) * gw))
        j = min(gh - 1, int((ry - y) / (2 * ry) * gh))
        out.append(j * gw + i)
    return out


@lru_cache(maxsize=4)
def _lut(color, glow):
    """Count level 0-255 -> premultiplied BGRA bytes, `color` ramping into `glow` at the densest."""
    r0, g0, b0, _ = vb.canvas.rgba(color)
    r1, g1, b1, _ = vb.canvas.rgba(glow)
    out = bytearray()
    for v in range(256):
        t = v / 255
        hot = max(0.0, (t - 0.55) / 0.45) ** 1.5
        r, g, b = (u + (w - u) * hot for u, w in ((r0, r1), (g0, g1), (b0, b1)))
        out += bytes((round(b * t * 255), round(g * t * 255), round(r * t * 255), round(t * 255)))
    return bytes(out)


def draw_clifford(cv, x, y, w, h, p=1.0, params=CLASSIC, points=600_000, color=demo.ACCENT,
                  glow=demo.INK, gain=1.0, grid=1.0):
    """Draw the Clifford attractor's density cloud fitted into the box
    (x, y, w, h), keeping its aspect. `p` (0 -> 1) is how much of the orbit
    has landed so far: the cloud fills in from faint scattered hops to the
    full shape. Density is shown on a log scale, from `color` at the thin
    edges to `glow` in the thickest folds; `gain` brightens it. `points` is
    the orbit length (more is smoother, slower to compute once); `grid`
    scales the density grid against device pixels (lower is softer).
    Returns the Box the cloud fills."""
    aspect = (1 + abs(params[2])) / (1 + abs(params[3]))
    bw, bh = (w, w / aspect) if w / h < aspect else (h * aspect, h)
    box = vb.Box(x + (w - bw) / 2, y + (h - bh) / 2, bw, bh)
    s = cv.scale_factor() * grid
    gw, gh = max(8, round(bw * s)), max(8, round(bh * s))
    bins = _bins(points, tuple(params), gw, gh)
    k = round(len(bins) * vb.clamp01(p))
    if k == 0:
        return box
    counts = [0] * (gw * gh)
    for cell in bins[:k]:
        counts[cell] += 1
    # Normalise against the finished cloud's density so the cloud brightens as it fills.
    ref = math.log1p(max(1, len(bins) / (gw * gh)) * 6)
    level = bytes(min(255, round(255 * gain * math.log1p(n) / ref)) for n in counts)
    im = Image.frombytes('L', (gw, gh), level)
    lut = _lut(color, glow)
    data = bytearray(b''.join(lut[v * 4:v * 4 + 4] for v in im.tobytes()))
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, gw, gh, gw * 4)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(box.x, box.y)
    ctx.scale(bw / gw, bh / gh)
    ctx.set_source_surface(surf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.rectangle(0, 0, gw, gh)
    ctx.fill()
    ctx.restore()
    return box


def draw(n, cv):
    p = demo.phase(n, 0.0, 2.5)
    box = draw_clifford(cv, 140, 60, demo.W - 280, demo.H - 120, p ** 1.8,
                        points=500_000, grid=0.75, gain=0.85)
    cv.mark('attractor', *box)
    # The live orbit: a short trail of the latest hops, flicking around the shape.
    if 0 < p < 1:
        rx, ry = 1 + abs(CLASSIC[2]), 1 + abs(CLASSIC[3])
        pts = clifford_points(12, start=(0.1 + n * 0.013, 0.1), skip=n % 7 + 20)
        for i, (px, py) in enumerate(pts):
            demo.dot(cv, box.x + (px + rx) / (2 * rx) * box.w, box.y + (ry - py) / (2 * ry) * box.h,
                     r=5, color=demo.TEAL, alpha=(1 - p) * (i + 1) / len(pts))


CAPABILITY = Capability(
    id='clifford-attractor',
    name='Clifford attractor',
    family='particles',
    group='Strange attractors',
    aliases=('Clifford map', 'Pickover attractor', 'Pickover popcorn', 'Pickover map'),
    definition='A single point is bounced over and over through a small sine-and-cosine formula, and the '
               'places it lands build up into a glowing, swirling ribbon of density.',
    phrasings=('a generative strange-attractor cloud that fills in like smoke',
               'those swirly math-art shapes made of millions of tiny dots',
               'iterate a chaotic equation and let the points paint a glowing shape'),
    related=('circle-pop', 'tesseract-rotation', 'sierpinski-gasket', 'swirl', 'gravity-well-attraction',
             'radial-repeater'),
    api=('videobuilder.capabilities.particles.clifford_attractor.draw_clifford',
         'videobuilder.capabilities.particles.clifford_attractor.clifford_points',
         'videobuilder.capabilities.particles.clifford_attractor.clifford_step'),
    demo=lambda: demo.film(draw),
)

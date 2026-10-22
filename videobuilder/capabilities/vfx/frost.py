"""Frost: feathery ice fronds creep in from the edges of the frame, branching
as they go, while a pale haze builds behind them so the picture underneath
is half hidden, like a window on a winter morning."""
import functools
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ICE = '#eef6ff'


def _frond(out, rng, x, y, ang, length, t0, dur, width, depth):
    """Append one frond to `out`: a gently curving spine from (x, y) heading
    `ang`, with barbs on both sides that shorten toward the tip, and (when
    `depth` allows) a few smaller fronds sprouting off it. Each segment is
    `(x0, y0, x1, y1, t0, t1, width)`, `t0`/`t1` the growth progress at which
    it starts and finishes drawing."""
    steps = max(4, int(length / 11))
    seg = length / steps
    bend = rng.uniform(-0.012, 0.012)
    spread = rng.uniform(0.65, 0.9)
    for i in range(steps):
        f = i / steps
        a = ang + bend * i + rng.gauss(0, 0.04)
        nx, ny = x + seg * math.cos(a), y + seg * math.sin(a)
        s0, s1 = t0 + dur * f, t0 + dur * (i + 1) / steps
        out.append((x, y, nx, ny, s0, s1, width * (1 - 0.6 * f)))
        barb = length * 0.22 * (1 - f) ** 0.8 * rng.uniform(0.7, 1.1)
        if barb > 5 and i > 0:
            for side in (-1, 1):
                ba = a + side * spread
                bl = barb * rng.uniform(0.8, 1.0)
                ex, ey = x + bl * math.cos(ba), y + bl * math.sin(ba)
                out.append((x, y, ex, ey, s1, s1 + dur * 0.18, width * 0.45))
                if depth > 1 and bl > 26:  # tiny ticks along the barb: the feathery fringe
                    for k in (0.45, 0.75):
                        tx, ty = x + bl * k * math.cos(ba), y + bl * k * math.sin(ba)
                        for s in (-1, 1):
                            ta, tl = ba + s * 0.9, bl * 0.22
                            out.append((tx, ty, tx + tl * math.cos(ta), ty + tl * math.sin(ta),
                                        s1 + dur * 0.12, s1 + dur * 0.24, width * 0.3))
        if depth > 0 and i > 1 and rng.random() < 0.09:
            side = rng.choice((-1, 1))
            _frond(out, rng, x, y, a + side * rng.uniform(0.5, 0.9), length * (1 - f) * 0.55,
                   s1, dur * 0.6, width * 0.7, depth - 1)
        x, y = nx, ny


@functools.lru_cache(maxsize=8)
def frost_fronds(width, height, count=96, reach=0.42, seed=3):
    """Ice fronds rooted along all four edges of a `width` x `height` frame,
    each growing inward up to about `reach` of the shorter side (longer in the
    corners, where frost gathers first). Returns a tuple of segments
    `(x0, y0, x1, y1, t0, t1, width)` for `draw_frost`, `t0`/`t1` in 0..1.
    Deterministic for a given `seed`; cached, so a film can call it every frame."""
    rng = random.Random(seed)
    out = []
    short = min(width, height)
    perim = 2 * (width + height)
    for k in range(count):
        d = (k + rng.uniform(0.1, 0.9)) / count * perim
        if d < width:
            x, y, ang, along = d, 0.0, math.pi / 2, d / width
        elif d < width + height:
            x, y, ang, along = width, d - width, math.pi, (d - width) / height
        elif d < 2 * width + height:
            x, y, ang, along = width - (d - width - height), height, -math.pi / 2, (d - width - height) / width
        else:
            x, y, ang, along = 0.0, height - (d - 2 * width - height), 0.0, (d - 2 * width - height) / height
        corner = 1 - min(along, 1 - along) * 2  # 1 at a corner, 0 mid-edge
        length = short * reach * rng.uniform(0.5, 1.0) * (0.75 + 0.6 * corner)
        start = rng.uniform(0.0, 0.35) * (1 - 0.6 * corner)
        _frond(out, rng, x, y, ang + rng.gauss(0, 0.35), length, start, 1 - start - 0.25,
               rng.uniform(2.2, 3.2), 2)
    return tuple(out)


def frost_haze(cv, p, depth=0.3, color=ICE, alpha=0.55):
    """A pale fog rising in from every edge of the frame at progress `p`:
    strongest at the border, gone `depth` of the way in (as a fraction of the
    shorter side). The frosted glass the fronds sit on."""
    w, h = cv.width, cv.height
    d = min(w, h) * depth * (0.4 + 0.6 * vb.clamp01(p))
    a = alpha * vb.clamp01(p)
    r, g, b, _ = vb.canvas.rgba(color)
    c = cv.ctx
    for x0, y0, x1, y1 in ((0, 0, 0, d), (0, h, 0, h - d), (0, 0, d, 0), (w, 0, w - d, 0)):
        grad = cairo.LinearGradient(x0, y0, x1, y1)
        grad.add_color_stop_rgba(0, r, g, b, a)
        grad.add_color_stop_rgba(0.35, r, g, b, a * 0.45)
        grad.add_color_stop_rgba(1, r, g, b, 0)
        c.rectangle(0, 0, w, h)
        c.set_source(grad)
        c.fill()


def draw_frost(cv, p, fronds=None, color=ICE, alpha=0.9, haze=True, seed=3):
    """Frost over everything already drawn on `cv`, grown to progress `p`
    (0 = clear glass, 1 = fully frosted): fronds from `frost_fronds` (default:
    one sized to the canvas with `seed`) creep in from the edges, each segment
    stretching out as its moment arrives, over a `frost_haze` when `haze`."""
    p = vb.clamp01(p)
    if haze:
        frost_haze(cv, p, color=color)
    if p <= 0:
        return
    segs = fronds if fronds is not None else frost_fronds(cv.width, cv.height, seed=seed)
    c = cv.ctx
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    buckets = {}
    for x0, y0, x1, y1, t0, t1, wd in segs:
        if t0 >= p:
            continue
        f = 1.0 if p >= t1 else (p - t0) / (t1 - t0)
        buckets.setdefault(round(wd * 4) / 4, []).append((x0, y0, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    for wd, lines in buckets.items():  # one stroke per width: thousands of segments stay cheap
        c.new_path()
        for x0, y0, x1, y1 in lines:
            c.move_to(x0, y0)
            c.line_to(x1, y1)
        c.set_line_width(wd)
        c.stroke()


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    draw_frost(cv, demo.phase(n, 0.15, 2.85))


CAPABILITY = Capability(
    id='frost',
    name='Frost',
    family='vfx',
    group='Water & atmosphere',
    aliases=('window frost', 'ice bloom', 'frost crystals', 'frosted glass'),
    definition='Branching white ice fronds spread inward from the borders of the picture over a misty haze, '
               'gradually veiling the scene behind them.',
    phrasings=('make the screen freeze over with frost from the edges',
               'ice crystals creeping across the shot like a frozen window',
               'the picture frosts up as if it is getting really cold'),
    related=('snowfall', 'gooch-shading', 'fresnel-edge-glow', 'thin-film-iridescence', 'spiral-bloom',
             'rainfall'),
    api=('videobuilder.capabilities.vfx.frost.draw_frost',
         'videobuilder.capabilities.vfx.frost.frost_fronds',
         'videobuilder.capabilities.vfx.frost.frost_haze'),
    demo=lambda: demo.film(draw),
)

"""Jitter and Boil Text: the same idea as Line boil (`../shapes/line_boil.py`,
which keeps the capability) -- both re-wobble an outline every few frames as
if it were redrawn by hand; this one does it letter by letter, shifting each
one a pixel or two as well. This module's own code stays (a film may still
import it), but it is no longer a capability of its own."""
import math
import random
from functools import lru_cache

import cairo
from gi.repository import PangoCairo

import videobuilder as vb
from videobuilder.looks.fx import boil

from .. import _demo as demo

MERGED_INTO = 'line-boil'

_scratch = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))


@lru_cache(maxsize=512)
def _outline(ch, font, step=5.0):
    """The glyph `ch` as closed polygons, top-left of its line box at (0, 0),
    flattened and resampled so no edge is longer than `step` px (a long
    straight stem needs points along it to wobble)."""
    ctx = _scratch
    ctx.new_path()
    lh = vb.text.line_height(font)
    content, _ = vb.text._content(font)
    ctx.move_to(0, (lh - content) / 2)
    PangoCairo.layout_path(ctx, vb.text._layout(ctx, ch, font))
    polys, cur = [], []
    for kind, pts in ctx.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            if len(cur) > 2:
                polys.append(cur)
            cur = [pts]
        elif kind == cairo.PATH_LINE_TO:
            if cur:
                (x0, y0), (x1, y1) = cur[-1], pts
                k = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
                cur += [(x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k) for i in range(1, k + 1)]
            else:
                cur = [pts]
        elif kind == cairo.PATH_CLOSE_PATH:
            if len(cur) > 2:
                polys.append(cur)
            cur = [cur[0]] if cur else []
    if len(cur) > 2:
        polys.append(cur)
    ctx.new_path()
    return tuple(tuple(p) for p in polys)


def _field(seed, waves=4, wavelength=40.0):
    """A smooth seeded 2-D displacement field (x, y) -> (dx, dy) in about
    [-1, 1]: a few plane waves at random angles and phases."""
    rnd = random.Random(seed)
    def wave():
        a = rnd.uniform(0, 2 * math.pi)
        k = 2 * math.pi / (wavelength * rnd.uniform(0.6, 1.4))
        return k * math.cos(a), k * math.sin(a), rnd.uniform(0, 2 * math.pi)
    wx = [wave() for _ in range(waves)]
    wy = [wave() for _ in range(waves)]
    norm = 1 / math.sqrt(waves / 2)
    return lambda x, y: (norm * sum(math.sin(fx * x + fy * y + ph) for fx, fy, ph in wx),
                         norm * sum(math.sin(fx * x + fy * y + ph) for fx, fy, ph in wy))


def boil_text(text, font, x, y, t, seed=0, boil_amount=2.5, jitter=2.0, turn=1.5, per_second=12,
              wavelength=None):
    """`text` on one line from its top-left (x, y) at time `t` s, as filled
    polygons with a hand-drawn boil: a list of `[(px, py), ...]` outlines,
    one or more per letter. The outline is pushed up to `boil_amount` px by
    a smooth seeded field, and each letter shifted up to `jitter` px and
    turned up to `turn` degrees; all of it is drawn fresh `per_second` times
    a second (12: a hand-drawn rate) and holds between. `wavelength`: px of
    the wobble along an edge (default: a third of the font size). The same
    `seed` and `t` give the same frame."""
    k = boil(t, per_second)
    wl = wavelength or font.size / 3
    field = _field(f'{seed}:{k}', wavelength=wl)
    out, left = [], x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        if not ch.isspace():
            rnd = random.Random(f'{seed}:{k}:{i}')
            ox, oy = rnd.uniform(-jitter, jitter), rnd.uniform(-jitter, jitter)
            a = math.radians(rnd.uniform(-turn, turn))
            ca, sa = math.cos(a), math.sin(a)
            cx, cy = adv / 2, vb.text.line_height(font) / 2
            for poly in _outline(ch, font):
                pts = []
                for px, py in poly:
                    rx, ry = px - cx, py - cy
                    gx = left + cx + rx * ca - ry * sa + ox
                    gy = y + cy + rx * sa + ry * ca + oy
                    dx, dy = field(gx, gy)
                    pts.append((gx + dx * boil_amount, gy + dy * boil_amount))
                out.append(pts)
        left += adv
    return out


def draw_boil_text(cv, text, font, x, y, t, color, alpha=1.0, **kw):
    """Draw `text` boiling at time `t` from its top-left (x, y) in `color`.
    `kw` goes to `boil_text`. Returns the Box of the line at rest."""
    c = cv.ctx
    c.new_path()
    for poly in boil_text(text, font, x, y, t, **kw):
        c.move_to(*poly[0])
        for p in poly[1:]:
            c.line_to(*p)
        c.close_path()
    c.set_fill_rule(cairo.FILL_RULE_WINDING)
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.fill()
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(170, 900)
    text = 'BOIL'
    w, h = vb.text.block_size([text], f)
    box = draw_boil_text(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, n / demo.FPS, demo.INK,
                         seed=3, boil_amount=2.5, jitter=2.5, turn=1.5)
    cv.mark('text', *box)

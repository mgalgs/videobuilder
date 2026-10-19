"""Rack focus: the lines come out of a soft haze one after another, each
pulling into sharp focus as the one before blurs back, the way a lens racks
between two depths. Through the hold the focus keeps racking from line to
line (a single line breathes in and out of focus instead), an accent rule
glides to whichever line is sharp, and soft discs of out-of-focus light
drift behind. On the exit everything goes back into the haze.

A serif set as big as the frame allows, centred line by line. The blur is
a real Gaussian (kit.blurred), drawn small so a wide one stays cheap.
"""
import math
from functools import lru_cache

import cairo

from .. import text
from ..layout import Box
from ..text import Font
from . import kit
from .style import Clock, Style

RACK = 0.38             # of a slot, the focus pull's length


def _slot(p):
    n = len(p.lines)
    enter = min(0.6 * p.length, n * min(2.2, max(0.9, 0.42 * p.length / n)))
    return enter / n


def _clock(p):
    return Clock(p.length, enter=_slot(p) * len(p.lines))


@lru_cache(maxsize=64)
def _layout(lines, box, family):
    inner, w, h, k = kit.room(box, tall=(0.88, 0.5), wide=(0.78, 0.62), square=(0.84, 0.6))
    font = kit.fit(lines, lambda s: Font(family, s, weight=500, line_height=1.25), w, h)
    lh = text.line_height(font)
    top = inner.cy - lh * len(lines) / 2
    return font, lh, tuple((inner.cx - text.measure(ln, font) / 2, top + i * lh, text.measure(ln, font))
                           for i, ln in enumerate(lines))


def focus(p, t, clock=None):
    """Each line's (presence, focus) at `t`, both 0-1."""
    clock = clock or _clock(p)
    n, slot = len(p.lines), _slot(p)
    u = max(0.0, t) / slot
    k = int(u)
    e = kit.smooth((u - k) / RACK)
    out = []
    for i in range(n):
        here = kit.smooth((t - i * slot) / (slot * RACK * 1.4))
        if n == 1:
            f = e if t < clock.hold else 1 - 0.35 * (0.5 - 0.5 * math.cos(2 * math.pi * (t - clock.hold) / 2.6))
        elif k % n == i:
            f = e
        elif (k - 1) % n == i and k > 0:
            f = 1 - e
        else:
            f = 0.0
        q = clock.leaving(t)
        out.append((here * (1 - q), f * (1 - q)))
    return out


def _bokeh(cv, p, box, t):
    rnd = kit.rng('rack-focus', box.w, box.h)
    m = min(box.w, box.h)
    for i in range(16):
        r = m * rnd.uniform(0.04, 0.13)
        x = box.x + (rnd.uniform(-0.1, 1.1) * box.w + t * m * rnd.uniform(-0.05, 0.05)) % (box.w * 1.2) - box.w * 0.1
        y = box.y + rnd.uniform(0, 1) * box.h + math.sin(t * rnd.uniform(0.3, 0.7) + i) * m * 0.03
        col = p.accent if i % 3 else p.ink
        a = rnd.uniform(0.04, 0.10)
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0, *kit.rgba(col, a * 0.7))
        g.add_color_stop_rgba(0.8, *kit.rgba(col, a))
        g.add_color_stop_rgba(1, *kit.rgba(col, 0))
        cv.ctx.set_source(g)
        cv.ctx.arc(x, y, r, 0, 2 * math.pi)
        cv.ctx.fill()


def draw(cv, p, t, box, clock):
    box = Box(*box)
    font, lh, rows = _layout(p.lines, box, STYLE.font_family(p))
    if p.paper is not None:     # the haze is the ground's: over a picture, only the letters
        _bokeh(cv, p, box, t)
    states = focus(p, t, clock)
    blur_max = font.size * 0.11
    with cv.layer(**kit.camera(t, clock.hold, box.cx, box.cy, box, k=0.04)):
        for i, ((x, y, w), (here, f)) in enumerate(zip(rows, states)):
            if here <= 0.01:
                continue
            q = clock.leaving(t)
            radius = (1 - f) * blur_max + q * blur_max
            grow = 1 + 0.05 * (1 - f)
            alpha = here * (0.45 + 0.55 * f)
            line = p.lines[i]
            cx, cy = x + w / 2, y + lh / 2

            def paint(c, line=line, x=x, y=y, cx=cx, cy=cy, grow=grow):
                c.ctx.save()
                c.ctx.translate(cx, cy)
                c.ctx.scale(grow, grow)
                c.ctx.translate(-cx, -cy)
                text.draw(c, [line], font, x, y, p.ink)
                c.ctx.restore()
            kit.blurred(cv, Box(x - w * 0.04, y, w * 1.08, lh), radius, paint, alpha=alpha)
            if f > 0.85 and here > 0.95:
                cv.mark(f'line-{i}', x, y, w, lh)
        # The accent rule glides to the sharp line.
        weights = [f * here for here, f in states]
        total = sum(weights)
        if total > 0.05:
            content = text._content(font)[0]
            ry = sum(wt * (r[1] + lh / 2 + content * 0.5) for wt, r in zip(weights, rows)) / total
            rw = sum(wt * r[2] for wt, r in zip(weights, rows)) / total * 0.35
            cv.rect(box.cx - rw / 2, ry, rw, max(2.0, font.size * 0.04), p.accent, alpha=min(1.0, max(weights)))


STYLE = Style('rack-focus', 'Rack focus', 'each line pulls out of a soft haze into focus as the last one blurs back',
              draw, aliases=('rackfocus', 'focus pull', 'focus', 'blur in', 'soft focus'), clock=_clock,
              family='serif')

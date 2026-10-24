"""Line chart draw-on: the core of Self-drawing line chart with a callout
(`line_chart_callout.py`, which keeps the capability): a data line grows
left to right across ruled axes, a soft fill rising under it and each
point's marker and value popping in as the line's head passes. This
module's own code stays (a film may still import it), but it is no longer
a capability of its own."""
import math

import cairo

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo

MERGED_INTO = 'line-chart-callout'


def chart_points(box, values, lo=None, hi=None):
    """The (x, y) of each value plotted inside `box` (x, y, w, h): spread
    evenly left to right, `lo` at the bottom edge and `hi` at the top
    (defaulting to the values' own range)."""
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    span = (hi - lo) or 1.0
    x, y, w, h = box
    n = len(values)
    return [(x + (w * i / (n - 1) if n > 1 else w / 2), y + h - (v - lo) / span * h) for i, v in enumerate(values)]


def reveal_x(points, progress):
    """The part of `points` (left to right in x) up to `progress` (0 -> 1) of
    their x extent, ending exactly at the cut -- so the line advances at a
    steady pace across the chart however steep each segment is."""
    if len(points) < 2:
        return list(points)
    progress = vb.clamp01(progress)
    x0, x1 = points[0][0], points[-1][0]
    cut = x0 + (x1 - x0) * progress
    out = [points[0]]
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        if bx <= cut:
            out.append((bx, by))
            continue
        t = (cut - ax) / (bx - ax) if bx > ax else 0.0
        out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        break
    return out


def draw_line_chart(cv, box, values, progress, color=demo.ACCENT, width=4, lo=None, hi=None, fill=0.3,
                    head=demo.INK, labels=True, font=None):
    """Draw `values` as a line chart in `box`, drawn on to `progress` (0 -> 1,
    left to right): the line in `color`, a gradient fill under it (`fill`:
    its top opacity, 0 for none), a ring marker at each point reached that
    pops in with a small overshoot as the line arrives, its value above it when `labels`, and a
    dot in `head` riding the tip while it draws. Returns the tip's (x, y)."""
    pts = chart_points(box, values, lo, hi)
    shown = reveal_x(pts, progress)
    bx, by, bw, bh = box
    base = by + bh
    if fill > 0 and len(shown) >= 2:
        c = cv.ctx
        c.new_path()
        c.move_to(shown[0][0], base)
        for p in shown:
            c.line_to(*p)
        c.line_to(shown[-1][0], base)
        c.close_path()
        g = cairo.LinearGradient(0, by, 0, base)
        r, gr, b, _ = vb.rgba(color)
        g.add_color_stop_rgba(0, r, gr, b, fill)
        g.add_color_stop_rgba(1, r, gr, b, 0)
        c.set_source(g)
        c.fill()
    paths.draw(cv, shown, color, width=width)
    tip = shown[-1]
    f = font or demo.font(18, 800)
    step = bw / max(1, len(values) - 1)
    for (x, y), v in zip(pts, values):
        k = vb.clamp01((tip[0] - x) / (step * 0.3) + 1)  # grows as the head nears, full on arrival
        if k <= 0 or progress <= 0:
            continue
        s = vb.ease_out_back(k)
        cv.sector(x, y, 7 * s, 0, 2 * math.pi, demo.BG)
        cv.arc(x, y, 7 * s, 0, 2 * math.pi, color, width=3)
        if labels:
            txt = f'{v:g}'
            w, h = vb.text.block_size([txt], f)
            vb.text.draw(cv, [txt], f, x - w / 2, y - 14 - h - 6 * (1 - k), demo.INK, alpha=k)
    if head and 0 < progress < 1:
        cv.sector(tip[0], tip[1], 14, 0, 2 * math.pi, head, alpha=0.2)
        cv.sector(tip[0], tip[1], 6, 0, 2 * math.pi, head)
    return tip


VALUES = (42, 68, 55, 87, 61, 74, 49, 78)
CATS = 'ABCDEFGH'


def draw(n, cv):
    box = (110, 90, demo.W - 180, demo.H - 180)
    x, y, w, h = box
    axis = demo.mono(14, 500)
    for v in (0, 25, 50, 75, 100):
        gy = y + h - v / 100 * h
        cv.line(x, gy, x + w, gy, demo.MUTED if v == 0 else demo.LINE, width=2 if v == 0 else 1)
        tw, th = vb.text.block_size([str(v)], axis)
        vb.text.draw(cv, [str(v)], axis, x - 30 - tw, gy - th / 2, demo.MUTED)
    cat = demo.font(16, 700)
    for (px, _), c in zip(chart_points(box, VALUES, 0, 100), CATS):
        tw, _ = vb.text.block_size([c], cat)
        vb.text.draw(cv, [c], cat, px - tw / 2, y + h + 14, demo.MUTED)
    p = demo.phase(n, 0.3, 2.5)
    tip = draw_line_chart(cv, box, VALUES, p * p * (3 - 2 * p), lo=0, hi=100)
    cv.mark('tip', tip[0] - 8, tip[1] - 8, 16, 16)

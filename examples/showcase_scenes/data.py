"""Lumen's launch dashboard: one screen where the tiles spring in, the hero
number counts up, a gauge sweeps, the bars grow on the beat and the line
chart draws on to its callout. All the numbers are made up."""
import math

import videobuilder as vb
from videobuilder import Box, paths, text

from . import kit
from .kit import ACCENT, BG, CARD, FPB, INK, LINE, MUTED, TEAL, pick

LABEL = kit.font(24, 600)
SMALL = kit.font(22, 600)
VALUE_F = kit.mono(26, 700)

# ---- timing, frames into the shot (it slides in over its first beat) ----
TILES_IN = 8                  # the first tile's spring; the others follow 5 frames apart
COUNT = (14, 52)
GAUGE_AT = 20
BAR_BEATS = (2, 3, 4)          # each bar grows on its beat
LINE_DRAW = (58, 102)
CALLOUT = (104, 116)

BARS = (('Before', 6, MUTED), ('Month 1', 11, TEAL), ('Month 3', 17, ACCENT))
SERIES = (('Lumen', (2, 3, 3.5, 5, 7, 9, 12, 16, 21, 28, 37, 48), ACCENT),
          ('To-do app', (10, 11, 10, 12, 12, 13, 12, 14, 13, 14, 15, 15), MUTED),
          ('Notes app', (6, 7, 7, 6, 8, 8, 9, 8, 9, 10, 9, 10), MUTED))
YMAX = 50


def layout(st):
    """The header's box and the four tiles: number, gauge, bars, chart."""
    c = st.content
    head = Box(c.x, c.y, c.w, 58)
    grid = Box(c.x, head.bottom + 18, c.w, c.bottom - head.bottom - 18)
    gap = 22
    if st.wide:
        top_h = 206
        tw = (grid.w - 2 * gap) / 3
        row = [Box(grid.x + i * (tw + gap), grid.y, tw, top_h) for i in range(3)]
        chart = Box(grid.x, grid.y + top_h + gap, grid.w, grid.h - top_h - gap)
        return head, row + [chart]
    h1, h2 = 236, 236
    tw = (grid.w - gap) / 2
    number = Box(grid.x, grid.y, tw, h1)
    gauge = Box(grid.x + tw + gap, grid.y, tw, h1)
    bars = Box(grid.x, grid.y + h1 + gap, grid.w, h2)
    chart = Box(grid.x, bars.bottom + gap, grid.w, grid.bottom - bars.bottom - gap)
    return head, [number, gauge, bars, chart]


def _number(cv, inner, f):
    p = kit.prog(f, *COUNT, vb.ease_out_expo)
    big = kit.mono(min(120, inner.h * 0.52), 700, tracking=-0.04)
    value = f'{3.2 * p:.1f}×'
    w = text.measure('3.2×', big)
    lh = text.line_height(big)
    y = inner.y + 40
    kit.glow(cv, inner.x + w / 2, y + lh / 2, w * 0.9, ACCENT, 0.2 * p)
    text.draw(cv, value, big, inner.x + w - text.measure(value, big), y, INK)   # right-aligned: digits don't jump
    text.draw(cv, 'more tasks done a week', SMALL, inner.x, inner.bottom - text.line_height(SMALL), MUTED)


def _gauge(cv, inner, f):
    p = max(0.0, kit.spring(f, GAUGE_AT, vb.damped(0.7, hz=1.5)))
    r = min(inner.h - 40, inner.w) * 0.42
    cx, cy = inner.x + r + 8, inner.y + 40 + r
    width = r * 0.24
    cv.arc(cx, cy, r, 0, 2 * math.pi, LINE, width=width)
    a0 = -math.pi / 2
    if p > 0.001:
        cv.arc(cx, cy, r, a0, a0 + 2 * math.pi * 0.92 * min(p, 1.04), TEAL, width=width)
    num = kit.mono(r * 0.56, 700, tracking=-0.03)
    value = f'{92 * min(1, p):.0f}%'
    w = text.measure('92%', num)
    text.draw(cv, value, num, cx - w / 2 + w - text.measure(value, num), cy - text.line_height(num) / 2, INK)
    tx = cx + r + width / 2 + 22
    tf = kit.font(30, 800, tracking=-0.01, line_height=1.1)
    if inner.right - tx > 110:
        lines, (lw, lh) = kit.lines_of('done on time', tf, inner.right - tx)
        text.draw(cv, lines, tf, tx, cy - lh / 2, INK)


def _bars(cv, inner, f):
    top = max(v for _, v, _ in BARS) * 1.08
    area = Box(inner.x, inner.y + 38, inner.w, inner.h - 38)
    name_w = 110
    row = area.h / 3
    for i, (name, v, colour) in enumerate(BARS):
        g = max(0.0, kit.spring(f, BAR_BEATS[i] * FPB - 2, vb.damped(0.55, hz=2.2)))
        y = area.y + i * row + row * 0.16
        bh = row * 0.68
        text.draw(cv, name, SMALL, area.x, y + bh / 2 - text.line_height(SMALL) / 2, INK)
        bw = (area.w - name_w - 90) * v / top * g
        if bw > 1:
            cv.rect(area.x + name_w, y, bw, bh, colour, radius=8)
        text.draw(cv, f'{v * min(1, g):.0f} h', VALUE_F, area.x + name_w + bw + 12,
                  y + bh / 2 - text.line_height(VALUE_F) / 2, INK, alpha=vb.clamp01(g * 2))


def _chart(cv, inner, f, st):
    """The line chart, and the callout's box (or None before it lands)."""
    unit = text.measure('50k', SMALL)
    plot = Box(inner.x + unit + 16, inner.y + 46, inner.w - unit - 16 - pick(st, 120, 20), inner.h - 46 - 40)
    for k in (0, 25, 50):
        y = plot.bottom - plot.h * k / YMAX
        cv.rect(plot.x, y, plot.w, 2, LINE)
        lab = f'{k}k'
        text.draw(cv, lab, SMALL, plot.x - 12 - text.measure(lab, SMALL), y - text.line_height(SMALL) / 2, MUTED)
    for k, lab in ((0, 'wk 1'), (11, 'wk 12')):
        x = plot.x + plot.w * k / 11
        text.draw(cv, lab, SMALL, x - (0 if k == 0 else text.measure(lab, SMALL)), plot.bottom + 10, MUTED)
    t = vb.ease_in_out_quart(vb.clamp01((f - LINE_DRAW[0]) / (LINE_DRAW[1] - LINE_DRAW[0])))
    for name, values, colour in reversed(SERIES):
        pts = paths.resample([(plot.x + plot.w * i / 11, plot.bottom - plot.h * v / YMAX)
                              for i, v in enumerate(values)], 120)
        if t > 0:
            paths.draw(cv, paths.reveal(pts, t), colour, width=6 if colour == ACCENT else 3)
            if st.wide and t >= 1 and colour != ACCENT:
                ex, ey = pts[-1]
                text.draw(cv, name, SMALL, ex + 12, ey - 14 + (8 if name == 'To-do app' else -2), MUTED)
    k = kit.prog(f, *CALLOUT, vb.ease_out_back)
    if k <= 0:
        return None
    px, py = plot.right, plot.bottom - plot.h * 48 / YMAX
    cv.rect(px - 10 * k, py - 10 * k, 20 * k, 20 * k, ACCENT, radius=10 * k)
    cv.arc(px, py, 19 * k, 0, 2 * math.pi, ACCENT, width=3, alpha=0.5)
    lab_f = kit.font(30, 750)
    num_f = kit.mono(28, 600)
    bw = max(text.measure('Launch week', lab_f), text.measure('48k users', num_f))
    lx, ly = px - bw - pick(st, 70, 60), py + 12
    cv.line(px - 14, py + 6, lx + bw + 8, ly + 18, INK, width=2, alpha=vb.clamp01(k))
    with cv.layer(opacity=vb.clamp01(k)):
        text.draw(cv, 'Launch week', lab_f, lx, ly, INK)
        text.draw(cv, '48k users', num_f, lx, ly + 38, ACCENT)
    return Box(lx, ly, bw, 38 + text.line_height(num_f))


def dashboard(cv, s, st):
    cv.fill(BG)
    f = s.f
    head, tiles = layout(st)
    tf = kit.font(pick(st, 44, 44), 800, tracking=-0.02)
    text.draw(cv, 'Launch week', tf, head.x, head.y, INK)
    cv.mark('title', head.x, head.y, text.measure('Launch week', tf), text.line_height(tf))
    if st.wide:
        sub = 'Lumen beta · week 12'
        sw = text.measure(sub, LABEL)
        text.draw(cv, sub, LABEL, head.right - sw, head.y + 14, MUTED)
        cv.mark('sub', head.right - sw, head.y + 14, sw, text.line_height(LABEL))
    labels = ('Tasks finished', 'On time', 'Focus hours a week', 'Weekly active users')
    names = ('number', 'gauge', 'bars', 'chart')
    callout = None
    for i, (box, label, name) in enumerate(zip(tiles, labels, names)):
        p = kit.spring(f, TILES_IN + 5 * i, kit.BOUNCY)
        inner = box.pad(24, 20)
        with cv.layer(opacity=vb.clamp01(p * 1.4)), kit.scaled(cv, box.cx, box.cy, 0.9 + 0.1 * min(1.04, p)):
            cv.rect(*box, CARD, radius=20)
            cv.outline(*box, LINE, width=2, radius=20)
            text.draw(cv, label, LABEL, inner.x, inner.y, MUTED)
            if name == 'number':
                _number(cv, inner, f)
            elif name == 'gauge':
                _gauge(cv, inner, f)
            elif name == 'bars':
                _bars(cv, inner, f)
            else:
                callout = _chart(cv, inner, f, st)
        cv.mark(name, *box)
    if callout:
        cv.mark('callout', *callout)


SCENES = {'dashboard': dashboard}

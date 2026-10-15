"""The Type and data block: a kinetic headline, a counting stat, bars, a ring
gauge and a self-drawing line chart, all Lumen's launch numbers (made up)."""
import math

import videobuilder as vb
from videobuilder import Box, paths, text

from . import kit
from .kit import ACCENT, BG, FPB, FPS, INK, LINE, MUTED, TEAL, pick

LABEL = kit.font(28, 600)
CAPTION = kit.font(34, 600)
SMALL = kit.font(24, 600)


def _title(cv, st, copy, x, y, f, align='left', width=None, name='title'):
    p = min(1, kit.spring(f, -4))
    tf = kit.font(pick(st, 40, 44), 750, tracking=-0.015)
    with cv.layer(opacity=p):
        box = text.draw(cv, copy, tf, x, y, INK, align=align, width=width)
    cv.mark(name, *box)
    return box


# ---- kinetic typography: a balanced headline, word by word, its weight landing ----
KINETIC = 'Plan less.\nDo more.\nFeel calm.'


def kinetic(cv, s, st):
    cv.fill(BG)
    c = st.content
    size = pick(st, 112, 108)
    probe = kit.font(size, 850, tracking=-0.03, line_height=1.02)
    lines = text.wrap(KINETIC, probe, c.w, balance=True)
    space = text.measure('a a', probe) - text.measure('aa', probe)
    lh = text.line_height(probe)
    top = c.cy - lh * len(lines) / 2
    k = 0
    words = KINETIC.split()
    widths = []
    for li, line in enumerate(lines):
        # Lay each line out at its final weight, so words don't shuffle as they thicken.
        lw = text.measure(line, probe)
        x = c.cx - lw / 2
        widths.append(lw)
        for word in line.split(' '):
            ww = text.measure(word, probe) + space
            p = kit.prog(s.f, -2 + 5 * k, 12 + 5 * k, vb.ease_out_quint)
            if p > 0:
                f = kit.font(size, 200 + 650 * p, tracking=-0.03, line_height=1.02)
                colour = ACCENT if k == len(words) - 1 else INK
                with cv.layer(opacity=min(1, p * 1.6), dy=(1 - p) * 40):
                    text.draw(cv, word, f, x, top + li * lh, colour)
            x += ww
            k += 1
    w = max(widths)
    cv.mark('headline', c.cx - w / 2, top, w, lh * len(lines))


# ---- numbers that count up ----
def counting(cv, s, st):
    cv.fill(BG)
    c = st.content
    p = kit.prog(s.f, -2, 30, vb.ease_out_expo)
    value = f'{3.2 * p:.1f}×'
    big = kit.mono(pick(st, 250, 230), 700, tracking=-0.04)
    w = text.measure('3.2×', big)
    lh = text.line_height(big)
    cap = 'more tasks finished every week'
    cap_lines, (cw, ch) = kit.lines_of(cap, CAPTION, pick(st, 900, 520))
    block = lh + 10 + ch
    top = c.cy - block / 2
    kit.glow(cv, c.cx, top + lh / 2, 420, ACCENT, 0.18 * p)
    vw = text.measure(value, big)
    text.draw(cv, value, big, c.cx - w / 2 + (w - vw), top, INK)  # right-aligned: digits don't jump
    cv.mark('stat', c.cx - w / 2, top, w, lh)
    a = kit.prog(s.f, 4, 18)
    with cv.layer(opacity=a):
        text.draw(cv, cap_lines, CAPTION, c.cx - cw / 2, top + lh + 10, MUTED, align='center', width=cw)
    cv.mark('caption', c.cx - cw / 2, top + lh + 10, cw, ch)


# ---- bar charts: three bars on three beats, labelled directly ----
BARS = (('Before Lumen', 6, MUTED), ('Month 1', 11, TEAL), ('Month 3', 17, ACCENT))
VALUE_F = kit.mono(34, 700)


def bars(cv, s, st):
    cv.fill(BG)
    c = st.content
    head = _title(cv, st, 'Focus hours a week', c.x, c.y + pick(st, 0, 20), s.f)
    area = Box(c.x, head.bottom + pick(st, 50, 70), c.w, c.bottom - head.bottom - pick(st, 60, 80))
    top = max(v for _, v, _ in BARS) * 1.08
    for i, (name, v, colour) in enumerate(BARS):
        g = max(0.0, kit.spring(s.f, i * FPB - 2, vb.damped(0.55, hz=2.2)))
        num = f'{v * min(1, g):.0f} h'
        if st.wide:   # horizontal bars, labels on the left, values at the bar's end
            row = area.h / 3
            y = area.y + i * row + row * 0.18
            bh = row * 0.64
            x0 = area.x + 250
            text.draw(cv, name, LABEL, area.x, y + bh / 2 - text.line_height(LABEL) / 2, INK)
            bw = (area.w - 250 - 140) * v / top * g
            if bw > 1:
                cv.rect(x0, y, bw, bh, colour, radius=10)
            text.draw(cv, num, VALUE_F, x0 + bw + 18, y + bh / 2 - text.line_height(VALUE_F) / 2, INK,
                      alpha=vb.clamp01(g * 2))
            cv.mark(f'bar-{i}', area.x, y, area.w, bh)
        else:         # vertical columns, names under them, values on top
            col = area.w / 3
            x = area.x + i * col + col * 0.16
            bw = col * 0.68
            base = area.bottom - 50
            bh = (base - area.y - 60) * v / top * g
            if bh > 1:
                cv.rect(x, base - bh, bw, bh, colour, radius=10)
            nw = text.measure(num, VALUE_F)
            text.draw(cv, num, VALUE_F, x + bw / 2 - nw / 2, base - bh - 50, INK, alpha=vb.clamp01(g * 2))
            lw = text.measure(name, SMALL)
            text.draw(cv, name, SMALL, x + bw / 2 - lw / 2, base + 14, INK)
            cv.mark(f'bar-{i}', x, area.y, bw, area.h)


# ---- gauges and rings: one score on an arc ----
def gauge(cv, s, st):
    cv.fill(BG)
    c = st.content
    p = max(0.0, kit.spring(s.f, -2, vb.damped(0.8, hz=1.6)))
    r = pick(st, 210, 230)
    cx, cy = (c.x + c.w * 0.3, c.cy) if st.wide else (c.cx, c.y + c.h * 0.36)
    width = r * 0.2
    cv.arc(cx, cy, r, 0, 2 * math.pi, LINE, width=width)
    a0 = -math.pi / 2
    if p > 0.001:
        cv.arc(cx, cy, r, a0, a0 + 2 * math.pi * 0.92 * min(p, 1.04), TEAL, width=width)
    num = kit.mono(pick(st, 110, 120), 700, tracking=-0.03)
    value = f'{92 * min(1, p):.0f}%'
    w = text.measure('92%', num)
    vw = text.measure(value, num)
    text.draw(cv, value, num, cx - w / 2 + (w - vw), cy - text.line_height(num) / 2, INK)
    cv.mark('gauge', cx - r - width / 2, cy - r - width / 2, 2 * r + width, 2 * r + width)
    words = 'of tasks done on time'
    big = kit.font(pick(st, 56, 52), 800, tracking=-0.02, line_height=1.08)
    if st.wide:
        x, y, wid, align = cx + r + 90, cy - 70, c.right - (cx + r + 90), 'left'
    else:
        x, y, wid, align = c.x, cy + r + 70, c.w, 'center'
    lines, (lw, lh) = kit.lines_of(words, big, wid)
    a = kit.prog(s.f, 2, 16)
    with cv.layer(opacity=a):
        box = text.draw(cv, lines, big, x, y, INK, align=align, width=wid if align == 'center' else None)
        text.draw(cv, 'Lumen beta, week 12', LABEL, x, box.bottom + 18, MUTED, align=align,
                  width=wid if align == 'center' else None)
    cv.mark('words', x, y, wid if align == 'center' else lw, lh + 18 + text.line_height(LABEL))


# ---- self-drawing line chart with a callout ----
SERIES = (('Lumen', (2, 3, 3.5, 5, 7, 9, 12, 16, 21, 28, 37, 48), ACCENT),
          ('To-do app', (10, 11, 10, 12, 12, 13, 12, 14, 13, 14, 15, 15), MUTED),
          ('Notes app', (6, 7, 7, 6, 8, 8, 9, 8, 9, 10, 9, 10), MUTED))
YMAX = 50


def line_chart(cv, s, st):
    cv.fill(BG)
    c = st.content
    head = _title(cv, st, 'Weekly active users', c.x, c.y + pick(st, 0, 20), s.f)
    unit = text.measure('48k', LABEL)
    plot = Box(c.x + unit + 24, head.bottom + pick(st, 50, 80), c.w - unit - 24 - pick(st, 150, 10),
               c.bottom - head.bottom - pick(st, 110, 220))
    axes = kit.prog(s.f, -3, 6)
    with cv.layer(opacity=axes):
        for k in (0, 25, 50):
            y = plot.bottom - plot.h * k / YMAX
            cv.rect(plot.x, y, plot.w, 2, LINE)
            lab = f'{k}k'
            text.draw(cv, lab, LABEL, plot.x - 16 - text.measure(lab, LABEL), y - text.line_height(LABEL) / 2, MUTED)
        for k, lab in ((0, 'wk 1'), (11, 'wk 12')):
            x = plot.x + plot.w * k / 11
            lw = text.measure(lab, LABEL)
            text.draw(cv, lab, LABEL, x - (0 if k == 0 else lw), plot.bottom + 14, MUTED)
    cv.mark('axes', plot.x - unit - 24, plot.y - 20, plot.w + unit + 24, plot.h + 60)
    t = vb.ease_in_out_quart(vb.clamp01((s.f - 4) / 32))
    for name, values, colour in reversed(SERIES):
        pts = [(plot.x + plot.w * i / 11, plot.bottom - plot.h * v / YMAX) for i, v in enumerate(values)]
        pts = paths.resample(pts, 120)
        if t > 0:
            part = paths.reveal(pts, t)
            paths.draw(cv, part, colour, width=6 if colour == ACCENT else 4)
            if st.wide and t >= 1 and colour != ACCENT:
                ex, ey = pts[-1]
                text.draw(cv, name, kit.font(24, 600), ex + 14, ey - 16, MUTED)
    if not st.wide:  # no room at the line ends: say what the grey lines are under the chart
        with cv.layer(opacity=vb.clamp01(t * 3)):
            text.draw(cv, 'Grey: a to-do app and a notes app', SMALL, plot.x, plot.bottom + 64, MUTED)
    # The callout: a dot, a leader and the label, once the hero line has landed.
    k = kit.prog(s.f, 38, 48, vb.ease_out_back)
    if k > 0:
        px, py = plot.x + plot.w, plot.bottom - plot.h * 48 / YMAX
        cv.rect(px - 11 * k, py - 11 * k, 22 * k, 22 * k, ACCENT, radius=11 * k)
        cv.arc(px, py, 20 * k, 0, 2 * math.pi, ACCENT, width=3, alpha=0.5)
        lx, ly = px - pick(st, 260, 250), py + pick(st, 30, 70)
        cv.line(px - 14, py + 8, lx + 230, ly + 10, INK, width=2, alpha=k)
        lab_f = kit.font(32, 750)
        with cv.layer(opacity=vb.clamp01(k)):
            text.draw(cv, 'Launch week', lab_f, lx - 20, ly - 6, INK)
            text.draw(cv, '48k users', kit.mono(30, 600), lx - 20, ly + 36, ACCENT)
        cv.mark('callout', lx - 20, ly - 6, 250, 80)


SCENES = {
    'kinetic-typography': kinetic,
    'counting-numbers': counting,
    'bar-charts': bars,
    'gauges-and-rings': gauge,
    'line-chart-callout': line_chart,
}

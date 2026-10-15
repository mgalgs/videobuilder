"""Data: line chart with a callout. Faint gridlines rule themselves in, then
the line draws on with a glowing head, a soft gradient filling in beneath it
and each point ticking as the head passes. On the beat after it lands, one
point is called out: a ring pulses round it, a drop line falls to the
baseline, and a tag springs in with the point's label and value. The ring
keeps pulsing on every beat while the chart holds.

In 9:16 the tag is a large panel under the chart, joined to its point by the
drop line, so the tall frame holds chart above and reading below.

After `examples/capabilities/line-chart-callout.py` and the showcase
dashboard's chart tile.
"""
import math

import cairo

import videobuilder as vb
from videobuilder import Box, paths, text

from .. import kit
from ..schema import Component, Slot
from . import _data_util as du

FPB = du.FPB
GRID_IN = (0, 12)
DRAW = (6, 6 + 2 * FPB)          # the line draws on over two beats
DROP = (2 * FPB + 8, 3 * FPB)    # the drop line falls into the third beat...
TAG_AT = 3 * FPB - 3             # ...and the tag lands on it
TAG_SPRING = vb.damped(0.55, hz=2.6)
EDGE = 14                        # px the tag keeps from the plot's edge


def _nice_ceil(v):
    """The smallest round number (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8 x 10^k) >= v."""
    if v <= 0:
        return 0.0
    k = 10 ** math.floor(math.log10(v))
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * k >= v * (1 - 1e-9):
            return m * k
    return 10 * k


def _domain(values):
    """(lo, hi): zero always on the scale, both ends on round numbers."""
    lo = -_nice_ceil(-min(values) * 1.04) if min(values) < 0 else 0.0
    hi = _nice_ceil(max(values) * 1.04) if max(values) > 0 else 0.0
    if hi - lo < 1e-12:
        hi = 1.0
    return lo, hi


def _callout_index(data, values):
    at = data.get('callout_at')
    if at is None:
        return max(range(len(values)), key=lambda i: values[i])
    return min(len(values) - 1, max(0, round(at) - 1))


def _ellipsize(s, f, max_w):
    if text.measure(s, f) <= max_w:
        return s
    while s and text.measure(s + '…', f) > max_w:
        s = s[:-1]
    return s + '…' if s else ''


def _layout(cv, data):
    """Boxes for the title, the plot, the x labels' row and (9:16 only) the
    tag's band; and the type sizes for this format."""
    s = du.safe(cv)
    shape = du.kind_of(cv)
    title_lines, title_f = du.wrap_fit(data['title'], lambda z: kit.font(z, 800, tracking=-0.01), s.w,
                                       {'wide': 40, 'tall': 40, 'square': 32}[shape], 24,
                                       max_lines=1 if shape == 'wide' else 2) if data['title'] else ([], None)
    _, th = text.block_size(title_lines, title_f) if title_lines else (0, 0)
    axis_f = kit.mono(17, 500)
    cat_f = kit.font(17, 600)
    cat_h = text.line_height(cat_f) + 14
    top = s.y + (th + 28 if title_lines else 0)
    band = None
    bottom = s.bottom
    if shape == 'tall':
        band_h = 190
        band = Box(s.x, s.bottom - band_h, s.w, band_h)
        bottom = band.y - 34
    return dict(s=s, shape=shape, title_f=title_f, title_lines=title_lines, axis_f=axis_f, cat_f=cat_f,
                top=top, bottom=bottom, cat_h=cat_h, band=band)


def _tag_fonts(shape):
    if shape == 'tall':
        return kit.font(24, 600), lambda size: kit.mono(size, 700)
    return kit.font(19, 600), lambda size: kit.mono(size, 700)


def _place_tag(plot, px, py, w, h, line_pts):
    """Where a w x h tag goes: the spot in the plot, clear of the point's
    ring, that sits over the fewest points of the line (and under it, the
    gradient), the nearest such spot to (px, py) winning a tie."""
    ring = Box(px - 20, py - 20, 40, 40)
    best = None
    x0, x1 = plot.x + EDGE, plot.right - EDGE - w
    y0, y1 = plot.y + 4, plot.bottom - 6 - h
    steps = 14
    for i in range(steps + 1):
        for j in range(steps + 1):
            box = Box(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps, w, h)
            if box.intersects(ring, 0):
                continue
            hits = sum(1 for (lx, ly) in line_pts if box.pad(-10).contains(Box(lx, ly, 0, 0), 0))
            under = sum(1 for (lx, ly) in line_pts if box.x <= lx <= box.right and ly < box.y)
            dist = math.hypot(box.cx - px, box.cy - py)
            cost = hits * 1000 + under * 40 + dist
            if best is None or cost < best[0]:
                best = (cost, box)
    return best[1] if best else Box(x0, y0, w, h)


def _edge_point(box, px, py):
    """The point on `box`'s edge nearest (px, py)."""
    return min(max(px, box.x), box.right), min(max(py, box.y), box.bottom)


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    f = shot.f
    color = data['color']
    pairs = du.series_pairs(data['series'])
    labels = [p[0] for p in pairs]
    values = [float(p[1]) for p in pairs]
    n = len(values)
    L = _layout(cv, data)
    s, shape = L['s'], L['shape']

    # ---- title ----
    if L['title_lines']:
        t = du.prog(f, 0, 10)
        box = text.draw(cv, L['title_lines'], L['title_f'], s.x, s.y + 10 * (1 - t), kit.INK, alpha=t)
        cv.mark('title', *box)

    # ---- scale, gutter and plot ----
    lo, hi = _domain(values)
    unit = data['unit']
    ticks = [hi if hi > 0 else None, lo if lo < 0 else None, 0.0, hi / 2 if hi > 0 and lo == 0 else None]
    tick_text = [du.num(v) + (unit if v not in (None, 0.0) else '') if v is not None else None for v in ticks]
    gutter = max(text.measure(tt, L['axis_f']) for tt in tick_text if tt) + 12
    plot = Box(s.x + gutter, L['top'] + 8, s.w - gutter - 10, L['bottom'] - L['cat_h'] - L['top'] - 8)

    def y_of(v):
        return plot.bottom - (v - lo) / (hi - lo) * plot.h

    def x_of(i):
        return plot.x + (plot.w * i / (n - 1) if n > 1 else plot.w / 2)

    g = du.prog(f, *GRID_IN, vb.ease_out_quint)
    lh = text.line_height(L['axis_f'])
    used_y = []
    for v, tt in zip(ticks, tick_text):
        if tt is None:
            continue
        y = y_of(v)
        if any(abs(y - u) < lh + 2 for u in used_y):
            continue  # a tick squeezed against another (a tiny negative under a huge positive)
        used_y.append(y)
        cv.line(plot.x, y, plot.x + plot.w * g, y, kit.MUTED if v == 0 else kit.LINE, width=2 if v == 0 else 1,
                alpha=0.55 if v == 0 else 1)
        tw = text.measure(tt, L['axis_f'])
        box = text.draw(cv, [tt], L['axis_f'], plot.x - 12 - tw, y - lh / 2, kit.MUTED, alpha=g)
        cv.mark(f'axis-{tt}', *box)

    # ---- x labels: all of them if they fit, else the ends and the called-out one ----
    hero = _callout_index(data, values)
    cat_f = L['cat_f']
    slot_w = plot.w / max(1, n - 1)
    fits = all(text.measure(lab, cat_f) <= slot_w - 8 for lab in labels)
    shown = range(n) if fits else sorted({0, n - 1, hero})
    placed = []
    hero_cat = None
    for i in shown:
        room = slot_w - 8 if fits else min(plot.w / 3, s.w / 3)
        lab = _ellipsize(labels[i], cat_f, room)
        if not lab:
            continue
        w = text.measure(lab, cat_f)
        x = min(max(x_of(i) - w / 2, s.x), s.right - w)
        box = Box(x, plot.bottom + 14, w, text.line_height(cat_f))
        if any(box.intersects(p, 0) for p in placed):
            continue
        placed.append(box)
        if i == hero:
            hero_cat = box
        text.draw(cv, [lab], cat_f, box.x, box.y, kit.INK if i == hero else kit.MUTED, alpha=g)
        cv.mark(f'cat-{i}', *box)

    # ---- the line, its fill and its points ----
    pts = [(x_of(i), y_of(v)) for i, v in enumerate(values)]
    if n == 1:
        pts = [(plot.x, pts[0][1]), (plot.right, pts[0][1])]
    dense = paths.resample(pts, 160) if n > 1 else pts
    d = du.prog(f, *DRAW, vb.ease_in_out_quart)
    zero_y = y_of(0.0)
    if d > 0:
        shown_pts = paths.reveal(dense, d)
        if len(shown_pts) >= 2:
            ctx = cv.ctx
            ctx.new_path()
            ctx.move_to(shown_pts[0][0], zero_y)
            for p in shown_pts:
                ctx.line_to(*p)
            ctx.line_to(shown_pts[-1][0], zero_y)
            ctx.close_path()
            grad = cairo.LinearGradient(0, plot.y, 0, plot.bottom)
            cr, cg, cb, _ = vb.rgba(color)
            grad.add_color_stop_rgba(0, cr, cg, cb, 0.32)
            grad.add_color_stop_rgba(1, cr, cg, cb, 0.02)
            ctx.set_source(grad)
            ctx.fill()
            paths.draw(cv, shown_pts, color, width=5)
            hx, hy = shown_pts[-1]
            if d < 1:
                du.glow(cv, hx, hy, 30, color, 0.55)
                cv.rect(hx - 6, hy - 6, 12, 12, kit.INK, radius=6)
        head_x = shown_pts[-1][0] if shown_pts else plot.x
        for i, (x, y) in enumerate(pts if n > 1 else []):
            if x > head_x + 0.5:
                continue
            passed = (head_x - x) / max(1.0, plot.w) * (DRAW[1] - DRAW[0])
            k = min(1.0, du.spring(passed, 0, vb.damped(0.5, hz=4)))
            r = 5 * max(0.0, k)
            cv.rect(x - r, y - r, 2 * r, 2 * r, kit.BG, radius=r)
            cv.arc(x, y, r, 0, 2 * math.pi, color, width=3)
        cv.mark('line', plot.x, plot.y, plot.w, plot.h)

    # ---- the callout ----
    px, py = pts[hero] if n > 1 else (plot.cx, pts[0][1])
    drop = du.prog(f, *DROP, vb.ease_out_quint)
    if drop > 0:
        end_y = L['band'].y if L['band'] is not None else zero_y
        y1 = py + (end_y - py) * drop
        ctx = cv.ctx
        ctx.save()
        ctx.set_dash([5, 6])
        gaps = [(hero_cat.y - 4, hero_cat.bottom + 4)] if hero_cat is not None and end_y > hero_cat.y else []
        a = py + 10
        for g0, g1 in gaps + [(y1, y1)]:
            if min(g0, y1) > a:
                cv.line(px, a, px, min(g0, y1), kit.INK, width=2, alpha=0.55)
            a = max(a, g1)
        ctx.restore()
        since = f - DROP[0]
        if since >= 0:
            beat_phase = (since % FPB) / FPB
            cv.arc(px, py, 10 + 22 * beat_phase, 0, 2 * math.pi, color, width=3, alpha=0.8 * (1 - beat_phase))
        cv.rect(px - 8, py - 8, 16, 16, color, radius=8)
        cv.arc(px, py, 8, 0, 2 * math.pi, kit.INK, width=3)

    k = du.spring(f, TAG_AT, TAG_SPRING)
    if k > 0.02:
        label = data['callout_label'] or labels[hero]
        counted = values[hero] * vb.clamp01(du.prog(f, TAG_AT, TAG_AT + FPB))
        dec = du.decimals_of(values[hero])
        value_txt = du.num(counted, None if abs(values[hero]) >= 1e4 else dec) + unit
        final_txt = du.num(values[hero]) + unit
        label_f, mono_of = _tag_fonts(shape)
        if L['band'] is not None:
            band = L['band']
            vf = du.fit(final_txt, mono_of, band.w - 56, 76, 30)
            lab_lines = text.wrap(label, label_f, band.w - 56)[:2]
            lw, lh = text.block_size(lab_lines, label_f)
            vh = text.line_height(vf)
            card = Box(band.x, band.y, band.w, min(band.h, 28 + vh + 6 + lh + 28))
            ax, ay = card.cx, card.y
        else:
            vf = du.fit(final_txt, mono_of, min(260, plot.w * 0.5), 44 if shape == 'wide' else 34, 18)
            lab_lines = [_ellipsize(label, label_f, max(text.measure(final_txt, vf), 200))]
            lw, lh = text.block_size(lab_lines, label_f)
            vh = text.line_height(vf)
            cw = max(lw, text.measure(final_txt, vf)) + 32
            ch = 14 + lh + 2 + vh + 14
            card = _place_tag(plot, px, py, cw, ch, dense)
            ax, ay = card.cx, card.cy
            ex, ey = _edge_point(card, px, py)
            if math.hypot(ex - px, ey - py) > 22:
                lead = vb.clamp01(k)
                ang = math.atan2(ey - py, ex - px)
                sx, sy = px + 12 * math.cos(ang), py + 12 * math.sin(ang)
                cv.line(sx, sy, sx + (ex - sx) * lead, sy + (ey - sy) * lead, kit.INK, width=2, alpha=0.7)
        with cv.layer(opacity=vb.clamp01(k * 1.6)), du.scaled(cv, ax, ay, 0.7 + 0.3 * k):
            cv.shadow(*card, radius=16, dy=8, blur=24, color=(0, 0, 0, 0.45))
            cv.rect(*card, '#1d1f26', radius=16)
            cv.outline(*card, kit.LINE, width=2, radius=16)
            cv.rect(card.x, card.y + 14, 5, card.h - 28, color, radius=2)
            inner = card.pad(14, 16) if L['band'] is None else card.pad(28, 28)
            text.draw(cv, lab_lines, label_f, inner.x, inner.y, kit.MUTED)
            text.draw(cv, [value_txt], vf, inner.x, inner.y + lh + (6 if L['band'] is not None else 2), kit.INK)
            cv.mark('callout', *card)


COMPONENT = Component(
    id='line-callout',
    kind='data',
    description=('A line chart that draws itself on over a soft gradient fill, then calls out one point with a '
                 'pulsing ring, a drop line and a tag showing its label and value. For a trend with one moment '
                 'that matters.'),
    tags=('data', 'chart', 'line', 'trend', 'callout', 'time series'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('title', 'text', True, 'What the chart shows, e.g. "Weekly sign-ups".', max_length=44),
        Slot('series', 'series', True,
             '3 to 12 points in time order, as (label, number) pairs, e.g. ("Mar", 12). Short labels '
             '(up to ~6 characters) are all shown; longer ones show only at the ends and the called-out point.',
             min_count=3, max_count=12),
        Slot('callout_at', 'number', False, 'Which point to call out, counting from 1; defaults to the highest.'),
        Slot('callout_label', 'text', False,
             "The callout tag's caption, e.g. \"Launch week\"; defaults to that point's own label.", max_length=24),
        Slot('unit', 'text', False, 'A short unit shown after every value, e.g. "%", "k" or " ms".', max_length=6),
        Slot('color', 'color', False, 'Colour of the line, its fill and the callout.'),
    ),
    sample={'title': 'Weekly sign-ups after the redesign',
            'series': [('W1', 4.2), ('W2', 4.8), ('W3', 4.5), ('W4', 6.1), ('W5', 7.4), ('W6', 9.8),
                       ('W7', 12.6), ('W8', 11.9)],
            'callout_at': 7, 'callout_label': 'Launch week', 'unit': 'k', 'color': kit.ACCENT},
    draw=draw,
    overlap_ok=(('line', 'callout'),),
)

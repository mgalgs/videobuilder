"""Data: leaderboard. A ranked list counted down: the rows slide in from last
place up, one every half beat, each a big rank numeral, a label and a
horizontal bar printed in halftone dots that grows to its value. First place
lands last, on the beat: its bar is solid accent, its row lifts onto a card,
its numeral pops, and a hard-light gleam runs once along its bar.

Items are sorted biggest first whatever order they come in. Rows fill the
frame's height, so 9:16 gets tall, roomy rows rather than a short list with
empty bands.

Draws on `examples/capabilities/comic-halftone.py` (the dot fill),
`hard-light-sweep.py` (the gleam) and `staggered-reveals.py`.
"""
import math

import cairo

import videobuilder as vb
from videobuilder import Box, text

from .. import kit
from ..schema import Component, Slot
from . import _data_util as du

FPB = du.FPB
CARD = '#1d1f26'
ENTER = vb.damped(0.62, hz=2.6)
GROW = 10             # frames for a bar to grow after its row arrives
GLEAM = 12            # frames for the gleam to cross the top bar


def _top_at(n):
    """The frame first place lands on: a beat, late enough that the rows
    under it have each had their half beat."""
    return max(2, math.ceil((n - 1) / 2) + 1) * FPB


def _enter_at(rank, n):
    return _top_at(n) - 4 - rank * FPB // 2


def _sizes(shape, row_h):
    """Type and bar sizes for a row `row_h` tall."""
    scale = {'wide': 1.0, 'square': 0.86, 'tall': 1.2}[shape]
    k = min(1.0, row_h / (88 * scale))
    rank = round(min(row_h * 0.62, 52 * scale * (0.7 + 0.3 * k)))
    label = round(max(15, min(26 * scale, row_h * 0.3)))
    value = round(max(16, min(30 * scale, row_h * 0.34)))
    bar = max(10, min(34 * scale, row_h * 0.3))
    if shape == 'tall':
        value = round(label * 0.72)  # it rides the bar's tip, so it must leave the bars room
    return rank, label, value, bar


def _ellipsize(s, f, max_w):
    if text.measure(s, f) <= max_w:
        return s
    while s and text.measure(s + '…', f) > max_w:
        s = s[:-1]
    return s.rstrip() + '…' if s else ''


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    f = shot.f
    color = data['color']
    shape = du.kind_of(cv)
    s = du.safe(cv)
    pre, unit = data['prefix'], data['unit']
    items = sorted(du.series_pairs(data['items']), key=lambda p: -p[1])
    n = len(items)

    # ---- title ----
    top = s.y
    if data['title']:
        t = du.prog(f, 0, 12)
        size = {'wide': 40, 'tall': 42, 'square': 32}[shape]
        lines, tf = du.wrap_fit(data['title'], lambda z: kit.font(z, 800, tracking=-0.01), s.w, size, 24,
                                1 if shape == 'wide' else 2)
        box = text.draw(cv, lines, tf, s.x, s.y + 10 * (1 - t), kit.INK, alpha=t)
        cv.mark('title', *box)
        top = s.y + box.h + (24 if shape != 'tall' else 36)

    # ---- rows ----
    area = Box(s.x, top, s.w, s.bottom - top)
    gap = 10 if shape != 'tall' else 16
    row_h = min((area.h - gap * (n - 1)) / n, {'wide': 120, 'square': 110, 'tall': 190}[shape])
    rows, _ = area.stack([row_h] * n, gap=gap, align='center' if shape == 'tall' else 'top')
    rank_px, label_px, value_px, bar_h = _sizes(shape, row_h)
    rank_f = kit.mono(rank_px, 800, tracking=-0.04)
    label_f = kit.font(label_px, 700)
    finals = [(du.MINUS if v < 0 else '') + pre + du.num(abs(v)) + unit for _, v in items]
    value_f = du.fit(max(finals, key=len), lambda z: kit.mono(z, 700), s.w * 0.36, value_px, 14)
    value_w = max(text.measure(v, value_f) for v in finals)
    rank_w = text.measure('00', rank_f) + (18 if shape != 'square' else 12)
    # one label size for every row: the largest that fits them all, down to 70%
    label_room = s.w - 26 - rank_w - (0 if shape == 'tall' else value_w + 16)
    longest = max((lab for lab, _ in items), key=lambda lab: text.measure(lab, label_f))
    label_f = du.fit(longest, lambda z: kit.font(z, 700), label_room, label_px, max(14, round(label_px * 0.7)))

    lo = min(0.0, min(v for _, v in items))
    hi = max(0.0, max(v for _, v in items))
    if hi - lo < 1e-12:
        hi = lo + 1.0
    top_at = _top_at(n)

    for rank, ((label, v), row, final) in enumerate(zip(items, rows, finals)):
        at = _enter_at(rank, n)
        k = du.spring(f, at, ENTER)
        if k <= 0.01:
            continue
        hero = rank == 0
        dx = -48 * (1 - min(1.0, k))
        alpha = vb.clamp01(k * 1.8)
        inner = row.pad(0, 14, 0, 12)
        track = Box(inner.x + rank_w, inner.y, inner.w - rank_w, inner.h)
        # 9:16: the label gets the whole line and the value rides the bar's tip, so
        # the bars share the track with one value's width; elsewhere the value
        # sits at the line's right end and the bar has the whole track
        riding = shape == 'tall'
        bar_track = Box(track.x, track.y, track.w - value_w - 14, track.h) if riding else track
        lh = text.line_height(label_f) if riding else max(text.line_height(label_f), text.line_height(value_f))
        block_h = lh + 8 + bar_h
        y0 = row.cy - block_h / 2
        bar_y = y0 + lh + 8
        g = du.prog(f, at + 4, at + 4 + GROW, vb.ease_out_expo)

        def x_of(val):
            return bar_track.x + (val - lo) / (hi - lo) * bar_track.w

        with cv.layer(opacity=alpha, dx=dx):
            if hero:
                lift = du.prog(f, top_at - 2, top_at + 8)
                if lift > 0:
                    cv.shadow(*row, radius=16, dy=10, blur=26, color=(0, 0, 0, 0.5 * lift))
                    cv.rect(*row, CARD, radius=16, alpha=lift)
                    cv.outline(*row, kit.mix(kit.LINE, color, 0.6), width=2, radius=16, alpha=lift)
            # rank numeral
            rk = f'{rank + 1:02d}'
            pop = du.pop(f, top_at, 0.18) if hero else 1.0
            rh = text.line_height(rank_f)
            rx, ry = row.x + 14, row.cy - rh / 2
            with du.scaled(cv, rx + text.measure(rk, rank_f) / 2, row.cy, pop):
                text.draw(cv, [rk], rank_f, rx, ry, color if hero else kit.MUTED)
            # label
            lab = _ellipsize(label, label_f, track.w if riding else track.w - value_w - 16)
            text.draw(cv, [lab], label_f, track.x, y0 + (lh - text.line_height(label_f)) / 2, kit.INK if hero else kit.mix(kit.INK, kit.MUTED, 0.35))
            # bar: from zero to the value, halftone dots for the field, solid for the winner
            x0, x1 = x_of(0.0), x_of(v)
            x1 = x0 + (x1 - x0) * g
            bx, bw = min(x0, x1), abs(x1 - x0)
            cv.rect(bar_track.x, bar_y, bar_track.w, bar_h, kit.LINE, radius=bar_h / 2, alpha=0.35)
            if bw > 1:
                if hero:
                    cv.rect(bx, bar_y, bw, bar_h, color, radius=bar_h / 2)
                    gl = du.prog(f, top_at - 2, top_at - 2 + GLEAM, vb.ease_in_out_quart)
                    if 0 < gl < 1:
                        with cv.clip(bx, bar_y, bw, bar_h, radius=bar_h / 2):
                            ctx = cv.ctx
                            band = max(30, bar_h * 1.6)
                            gx = bx - band - bar_h + gl * (bw + 2 * band + bar_h)
                            ctx.new_path()
                            ctx.move_to(gx, bar_y)
                            ctx.line_to(gx + band, bar_y)
                            ctx.line_to(gx + band - bar_h, bar_y + bar_h)
                            ctx.line_to(gx - bar_h, bar_y + bar_h)
                            ctx.close_path()
                            ctx.set_source_rgba(1, 1, 1, 0.45)
                            ctx.fill()
                else:
                    with cv.clip(bx, bar_y, bw, bar_h, radius=bar_h / 2):
                        cv.rect(bx, bar_y, bw, bar_h, kit.mix(kit.LINE, kit.MUTED, 0.25))
                        ctx = cv.ctx
                        pitch = max(5.0, bar_h / 3.2)
                        ctx.set_source(vb.halftone_pattern(pitch, pitch * 0.34, angle=0.4,
                                                           color=kit.mix(kit.MUTED, kit.INK, 0.2)))
                        ctx.paint()
                        ctx.set_operator(cairo.OPERATOR_OVER)
            if v == 0 and g > 0:
                cv.rect(x0 - 2, bar_y - 3, 4, bar_h + 6, kit.MUTED)
            # value, counted with the bar
            shown = (du.MINUS if v < 0 else '') + pre + du.num(abs(v) * g, None if abs(v) >= 1e4 else
                                                                du.decimals_of(v)) + unit
            vh = text.line_height(value_f)
            if riding:
                vx = max(x0, x1) + 12 if v >= 0 else bar_track.right + 14
                vy = bar_y + bar_h / 2 - vh / 2
            else:
                vx, vy = inner.right - text.measure(shown, value_f), y0 + (lh - vh) / 2
            text.draw(cv, [shown], value_f, vx, vy, kit.INK if hero else kit.MUTED)
        cv.mark(f'row-{rank + 1}', row.x + dx, row.y, row.w, row.h)


COMPONENT = Component(
    id='leaderboard',
    kind='data',
    description=('A ranked list counted down from last place: rows slide in every half beat with big rank '
                 'numerals and halftone bars; first place lands last on the beat, on a lifted card with a '
                 'solid accent bar and a light gleam. For a top-N ranking.'),
    tags=('data', 'ranking', 'leaderboard', 'top list', 'bars', 'halftone'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 7),
    slots=(
        Slot('title', 'text', True, 'What is ranked, e.g. "Most requested features".', max_length=40),
        Slot('items', 'series', True,
             '3 to 6 (label, number) pairs in any order; shown biggest first. Labels up to ~22 characters '
             'show in full.', min_count=3, max_count=6),
        Slot('prefix', 'text', False, 'Put before each value, e.g. "$".', max_length=2),
        Slot('unit', 'text', False, 'Put after each value, e.g. "%", "k" or " votes".', max_length=6),
        Slot('color', 'color', False, 'Colour of first place.'),
    ),
    sample={'title': 'Most requested features',
            'items': [('Offline mode', 412), ('Shared lists', 251), ('Dark theme', 388), ('Quick search', 197),
                      ('Home-screen widgets', 96)],
            'prefix': '', 'unit': ' votes', 'color': kit.ACCENT},
    draw=draw,
)

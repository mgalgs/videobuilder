"""Data: before / after. Two torn paper scraps drop onto the frame a beat
apart, each holding one value -- the old one on grey stock, the new one on
cream -- and a hand-drawn arrow strokes itself from the first to the second.
On the next beat a rubber stamp slams down beside the arrow with the change
between them (+68%, 12x, -4.5), the scraps jolting under it.

The scraps sit side by side in 16:9, fall down the frame in 9:16 (old above,
new below, the arrow curving between them) and lie corner to corner in 1:1.

Its own paper look (after `examples/capabilities/paper-collage.py`): grain,
torn edges and soft shadows, on the compendium's dark ground, with the
accent colour for the arrow and the stamp.
"""
import math
from functools import lru_cache

import cairo

import videobuilder as vb
from videobuilder import Box, paths, text

from .. import kit
from ..schema import Component, Slot
from . import _data_util as du

FPB = du.FPB
PAPER_OLD = '#cfc8bc'
PAPER_NEW = '#f4ecd8'
PAPER_INK = '#15120f'
PAPER_MUTED = '#6a6258'

BEFORE_AT = 2
AFTER_AT = FPB - 2               # the new scrap lands on the first beat
ARROW = (FPB + 6, 2 * FPB + 8)   # the arrow strokes on through the second beat
STAMP_AT = 3 * FPB               # the stamp hits on the third
DROP = vb.damped(0.55, hz=2.4)


def _delta_text(before, after, suffix):
    """The change, as short as it reads: a percentage, a multiple once it
    passes 10x, or a plain signed difference when there's no base to divide by."""
    if before == 0:
        if after == 0:
            return '±0'
        return du.num(after, signed=True) + suffix
    if before > 0 and after > 0 and after / before >= 10:
        return du.num(round(after / before, 1)) + '×'
    r = (after - before) / abs(before) * 100
    r = round(r) if abs(r) >= 10 else round(r, 1)
    if r == 0:
        return '±0%'
    return du.num(r, signed=True) + '%'


def _layout(cv):
    """Per format: the title's width and sizes, each scrap's centre, size and
    tilt, the stamp's centre and radius, and the arrow's start, control point
    and end. `area` is what's below the title."""
    s = du.safe(cv)
    shape = du.kind_of(cv)
    if shape == 'wide':
        return dict(shape=shape, title=(40, 26, 1), num=(78, 30), lab=19, area_top=s.y + 70,
                    before=(Box(s.x + 8, 0, 316, 240), -3.0), after=(Box(s.right - 352, 0, 344, 270), 2.5),
                    stamp_r=74)
    if shape == 'tall':
        return dict(shape=shape, title=(42, 28, 2), num=(84, 30), lab=21, area_top=s.y + 130,
                    before=(Box(s.x + 4, 0, 330, 190), -3.0), after=(Box(s.right - 382, 0, 378, 222), 2.0),
                    stamp_r=80)
    return dict(shape=shape, title=(32, 22, 2), num=(56, 22), lab=16, area_top=s.y + 92,
                before=(Box(s.x + 6, 0, 246, 146), -3.0), after=(Box(s.right - 268, 0, 262, 156), 2.0),
                stamp_r=62)


def _place(cv, L):
    """Concrete boxes for the two scraps, the stamp and the arrow, in the area
    under the title."""
    s = du.safe(cv)
    area = Box(s.x, L['area_top'], s.w, s.bottom - L['area_top'])
    (b, b_tilt), (a, a_tilt) = L['before'], L['after']
    r = L['stamp_r']
    if L['shape'] == 'wide':
        cy = area.cy
        b = Box(b.x, cy - b.h / 2 + 12, b.w, b.h)
        a = Box(a.x, cy - a.h / 2 - 6, a.w, a.h)
        gap_cx = (b.right + a.x) / 2
        stamp = (gap_cx, min(area.bottom - r - 6, cy + 74))
        arrow = ((b.right - 26, b.y + 40), (gap_cx, area.y - 10), (a.x + 6, a.y + 52))
    elif L['shape'] == 'tall':
        b = Box(b.x, area.y + 14, b.w, b.h)
        a = Box(a.x, area.bottom - a.h - 10, a.w, a.h)
        mid = (b.bottom + a.y) / 2
        stamp = (s.x + r + 18, mid + 2)
        arrow = ((b.right - 70, b.bottom + 6), (s.right + 6, mid - 30), (a.cx + 40, a.y - 14))
    else:
        b = Box(b.x, area.y + 6, b.w, b.h)
        a = Box(a.x, area.bottom - a.h - 6, a.w, a.h)
        stamp = (s.x + r + 6, area.bottom - r - 10)
        arrow = ((b.right - 18, b.cy + 24), (s.right - 30, b.cy + 10), (a.cx + 26, a.y - 10))
    return area, (b, b_tilt), (a, a_tilt), stamp, arrow


@lru_cache(maxsize=32)
def _scrap_points(w, h, seed):
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return tuple(paths.torn(pts, seed=seed, amount=5.0))


@lru_cache(maxsize=8)
def _stamp_points(r, seed):
    pts = [(r * math.cos(2 * math.pi * i / 64), r * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    return tuple(paths.torn(pts, seed=seed, amount=2.4, step=2.0))


@lru_cache(maxsize=16)
def _arrow_points(p0, c, p1):
    pts = []
    for i in range(48):
        t = i / 47
        u = 1 - t
        pts.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
    return tuple(paths.jitter(pts, seed=4, amount=2.0, wander=0.25))


def _fill(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def _grain(cv, alpha, seed):
    ctx = cv.ctx
    pat = vb.paper_grain(cv.width, cv.height, seed=seed)
    # centre the piece in the tile, so no tile seam crosses it
    pat.set_matrix(cairo.Matrix(x0=cv.width / 2, y0=cv.height / 2))
    ctx.set_source(pat)
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)


def _scrap(cv, name, box, tilt, k, jolt, paper, label, value_txt, L, seed):
    """One paper scrap dropping in (k: its spring, 0 -> 1), with its label and
    value, marked as one block."""
    if k <= 0.01:
        return
    lift = 16 * max(0.0, 1 - k)
    cx, cy = box.cx, box.cy - 46 * (1 - min(1.0, k)) + jolt
    angle = math.radians(tilt + 7 * (1 - min(1.0, k)))
    pts = _scrap_points(round(box.w), round(box.h), seed)
    ctx = cv.ctx
    with cv.layer(opacity=vb.clamp01(k * 2.5)):
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(angle)
        cv.shape_shadow(list(pts), dx=3 + lift * 0.4, dy=6 + lift, blur=12 + lift, color=(0, 0, 0, 0.55))
        _fill(ctx, pts)
        ctx.set_source_rgba(*vb.rgba(paper))
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        _grain(cv, 0.6, seed)
        ctx.restore()
        ctx.new_path()
        inner = Box(-box.w / 2, -box.h / 2, box.w, box.h).pad(22, 26)
        lab, lab_f = du.wrap_fit(label.upper(), lambda z: kit.font(z, 700, tracking=0.12), inner.w, L['lab'], 12, 1)
        text.draw(cv, lab, lab_f, inner.x, inner.y, PAPER_MUTED)
        hi, lo = L['num']
        num_f = du.fit(value_txt, lambda z: kit.font(z, 800, tracking=-0.03), inner.w, hi, lo)
        nh = text.line_height(num_f)
        text.draw(cv, [value_txt], num_f, inner.x, inner.bottom - nh, PAPER_INK)
        cv.mark(name, -box.w / 2 - 4, -box.h / 2 - 4, box.w + 8, box.h + 8)
        ctx.restore()


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    f = shot.f
    color = data['color']
    L = _layout(cv)
    s = du.safe(cv)
    area, (b, b_tilt), (a, a_tilt), (sx, sy), arrow = _place(cv, L)

    # ---- title ----
    if data['title']:
        t = du.prog(f, 0, 12)
        lines, tf = du.wrap_fit(data['title'], lambda z: kit.font(z, 800, tracking=-0.01), s.w, *L['title'])
        box = text.draw(cv, lines, tf, s.x, s.y + 10 * (1 - t), kit.INK, alpha=t)
        cv.mark('title', *box)

    before, after = float(data['before']), float(data['after'])
    pre, suf = data['prefix'], data['suffix']

    def money(v):
        sign = du.MINUS if v < 0 else ''
        return sign + pre + du.num(abs(v)) + suf

    # the stamp's hit jolts both scraps for a moment
    since = f - STAMP_AT
    jolt = 5 * math.exp(-since / 3) * math.cos(since * 1.6) if since >= 0 else 0.0
    _scrap(cv, 'before', b, b_tilt, du.spring(f, BEFORE_AT, DROP), jolt * 0.6, PAPER_OLD,
           data['before_label'] or 'Before', money(before), L, seed=3)
    _scrap(cv, 'after', a, a_tilt, du.spring(f, AFTER_AT, DROP), jolt, PAPER_NEW,
           data['after_label'] or 'After', money(after), L, seed=8)

    # ---- the arrow, stroked on by hand ----
    t = du.prog(f, *ARROW, vb.ease_in_out_quart)
    if t > 0:
        pts = list(_arrow_points(*arrow))
        paths.draw(cv, paths.reveal(pts, t), color, width=6)
        if t >= 1:
            (hx, hy), (px, py) = pts[-1], pts[-6]
            ang = math.atan2(hy - py, hx - px)
            for side in (-1, 1):
                b_ang = ang + math.pi + side * 0.5
                paths.draw(cv, [(hx + 22 * math.cos(b_ang), hy + 22 * math.sin(b_ang)), (hx, hy)], color, width=6)

    # ---- the stamp ----
    if since >= -4:
        r = L['stamp_r']
        hit = vb.clamp01((since + 4) / 4)
        scale = 1.9 - 0.9 * hit ** 2 if hit < 1 else du.pop(f, STAMP_AT, 0.06)
        ctx = cv.ctx
        with cv.layer(opacity=vb.clamp01(hit * 2)):
            ctx.save()
            ctx.translate(sx, sy)
            ctx.scale(scale, scale)
            ctx.rotate(math.radians(-9))
            pts = _stamp_points(r, 21)
            cv.shape_shadow(list(pts), dx=2, dy=5 * scale, blur=10, color=(0, 0, 0, 0.5))
            _fill(ctx, pts)
            ctx.set_source_rgba(*vb.rgba(color))
            ctx.fill_preserve()
            ctx.save()
            ctx.clip()
            _grain(cv, 0.45, 5)
            ctx.restore()
            ctx.new_path()
            cv.arc(0, 0, r * 0.82, 0, 2 * math.pi, PAPER_NEW, width=2.5, alpha=0.9)
            delta = _delta_text(before, after, suf)
            df = du.fit(delta, lambda z: kit.font(z, 900, tracking=-0.03), r * 1.38, round(r * 0.62), 14)
            dw, dh = text.measure(delta, df), text.line_height(df)
            text.draw(cv, [delta], df, -dw / 2, -dh / 2, PAPER_NEW)
            ctx.restore()
        cv.mark('stamp', sx - r * scale, sy - r * scale, 2 * r * scale, 2 * r * scale)


COMPONENT = Component(
    id='before-after',
    kind='data',
    description=('Two torn paper scraps drop in a beat apart, the old value on grey stock and the new one on '
                 'cream; a hand-drawn arrow joins them and a rubber stamp slams down with the change '
                 '(+68%, 12x). For a single before-and-after number.'),
    tags=('data', 'comparison', 'before after', 'change', 'delta', 'paper', 'collage'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('title', 'text', True, 'What changed, e.g. "Checkout time".', max_length=40),
        Slot('before', 'number', True, 'The old value.'),
        Slot('after', 'number', True, 'The new value.'),
        Slot('before_label', 'text', False, 'Caption on the old scrap; defaults to "Before". E.g. "Last year".',
             max_length=16),
        Slot('after_label', 'text', False, 'Caption on the new scrap; defaults to "After". E.g. "This year".',
             max_length=16),
        Slot('prefix', 'text', False, 'Put before each value, e.g. "$".', max_length=2),
        Slot('suffix', 'text', False, 'Put after each value, e.g. "s", "%" or " ms".', max_length=4),
        Slot('color', 'color', False, 'Colour of the arrow and the stamp.'),
    ),
    sample={'title': 'Time to first answer', 'before': 42, 'after': 13.5, 'before_label': 'Spring',
            'after_label': 'Autumn', 'prefix': '', 'suffix': 's', 'color': kit.ACCENT},
    draw=draw,
)

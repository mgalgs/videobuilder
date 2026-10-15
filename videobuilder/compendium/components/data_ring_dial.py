"""Data: ring dial. A gauge built from fifty-odd radial ticks on a 270-degree
arc: the empty ticks rise into place one after another round the dial, then
a lit sweep runs up them to the reading, its leading tick stretched and
glowing, while the number inside counts up with it. The sweep lands on a
beat, and the whole dial pops with a flash ring as it does. An optional
target sits on the dial as a small notch, so a reading can be seen against
its goal.

The dial sits beside its caption in 16:9 and above it in 9:16 and 1:1.

After `examples/capabilities/gauges-and-rings.py` and the showcase
dashboard's gauge tile.
"""
import math

import videobuilder as vb
from videobuilder import Box, text

from .. import kit
from ..schema import Component, Slot
from . import _data_util as du

FPB = du.FPB
TICKS = 54
START = math.radians(135)       # bottom left; canvas angles run clockwise
SWEEP = math.radians(270)
RISE = (0, 14)                   # the empty ticks rise in round the dial
FILL = (8, 3 * FPB)              # the sweep, landing on the third beat
LAND = FILL[1]
CAPTION_AT = FPB - 4             # the caption springs in near the first beat
CAPTION_SPRING = vb.damped(0.7, hz=2.2)


def _fraction(value, out_of):
    if out_of is None or out_of <= 0:
        return 1.0 if value > 0 else 0.0
    return vb.clamp01(value / out_of)


def _layout(cv, data):
    """The dial's centre and outer radius, and the caption's box and fonts."""
    s = du.safe(cv)
    shape = du.kind_of(cv)
    has_detail = bool(data['detail'])
    if shape == 'wide':
        r = min(s.h / 2, 222)
        dial = Box(s.x, s.cy - r, 2 * r, 2 * r)
        cap = Box(dial.right + 44, s.y, s.right - dial.right - 44, s.h)
        sizes = dict(label=(44, 26, 3), detail=(24, 18, 3))
        return s, shape, dial, cap, sizes, 'left'
    sizes = dict(label=(44, 28, 3), detail=(28, 20, 3)) if shape == 'tall' else \
        dict(label=(30, 22, 2), detail=(20, 16, 2))
    lab_lines, lab_f = du.wrap_fit(data['label'], _label_font, s.w, *sizes['label'])
    cap_h = text.block_size(lab_lines, lab_f)[1]
    if has_detail:
        det_lines, det_f = du.wrap_fit(data['detail'], _detail_font, s.w, *sizes['detail'])
        cap_h += 12 + text.block_size(det_lines, det_f)[1]
    gap = 40 if shape == 'tall' else 18
    r = min(s.w / 2, (s.h - cap_h - gap) / 2, 240 if shape == 'tall' else 999)
    total = 2 * r + gap + cap_h
    top = s.y + (s.h - total) / 2 if shape == 'tall' else s.y
    dial = Box(s.cx - r, top, 2 * r, 2 * r)
    cap = Box(s.x, dial.bottom + gap, s.w, cap_h)
    return s, shape, dial, cap, sizes, 'center'


def _label_font(size):
    return kit.font(size, 800, tracking=-0.01)


def _detail_font(size):
    return kit.font(size, 500)


def _angle(t):
    return START + SWEEP * t


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    f = shot.f
    color = data['color']
    value = float(data['value'])
    out_of = data['out_of'] if data['out_of'] is not None else 100.0
    target = _fraction(data['target'], out_of) if data['target'] is not None else None
    s, shape, dial, cap, sizes, align = _layout(cv, data)
    cx, cy, R = dial.cx, dial.cy, dial.w / 2

    tick_w = 2 * math.pi * R / (TICKS * 360 / 270) * 0.42
    r_out, r_in = R - 12, R - 12 - max(18, R * 0.16)
    goal = _fraction(value, out_of)
    sweep = goal * du.prog(f, *FILL, vb.ease_in_out_quart)
    pop = du.pop(f, LAND, 0.06) if goal > 0 else 1.0

    with du.scaled(cv, cx, cy, pop):
        # the flash ring: once, as the sweep lands
        since = f - LAND
        if goal > 0 and 0 <= since < FPB:
            k = since / FPB
            cv.arc(cx, cy, r_out + 4 + 26 * vb.ease_out_expo(k), 0, 2 * math.pi, color, width=4 * (1 - k) + 1,
                   alpha=0.6 * (1 - k))

        # inner orbit: a dashed ring turning slowly, for life while the dial holds
        ctx = cv.ctx
        ctx.save()
        ctx.set_dash([3, 9])
        spin = f * 0.012
        cv.arc(cx, cy, r_in - 16, spin, spin + 2 * math.pi, kit.LINE, width=2)
        ctx.restore()

        for i in range(TICKS):
            t = i / (TICKS - 1)
            appear = du.prog(f, RISE[0] + t * (RISE[1] - RISE[0]) * 0.7, RISE[0] + t * (RISE[1] - RISE[0]) * 0.7 + 6)
            if appear <= 0:
                continue
            a = _angle(t)
            lit = sweep > 0 and t <= sweep + 1e-9
            lead = lit and (t + 1 / (TICKS - 1) > sweep) and sweep < goal - 1e-6
            ro = r_out + (10 if lead else 0)
            ri = r_out - (r_out - r_in) * appear
            col = kit.mix(kit.mix(color, kit.BG, 0.45), color, t / max(sweep, 1e-6)) if lit else kit.LINE
            cos, sin = math.cos(a), math.sin(a)
            cv.ctx.set_line_cap(1)  # round
            cv.line(cx + ri * cos, cy + ri * sin, cx + ro * cos, cy + ro * sin, col, width=tick_w)
            cv.ctx.set_line_cap(0)
            if lead:
                du.glow(cv, cx + ro * cos, cy + ro * sin, 26, color, 0.6)

        if target is not None:
            a = _angle(target)
            cos, sin = math.cos(a), math.sin(a)
            tip = r_out + 8
            pts = [(cx + tip * cos, cy + tip * sin)]
            for side in (-1, 1):
                b = a + side * 0.07
                pts.append((cx + (tip + 16) * math.cos(b), cy + (tip + 16) * math.sin(b)))
            ctx = cv.ctx
            ctx.new_path()
            ctx.move_to(*pts[0])
            ctx.line_to(*pts[1])
            ctx.line_to(*pts[2])
            ctx.close_path()
            ctx.set_source_rgba(*vb.rgba(kit.INK, du.prog(f, *RISE)))
            ctx.fill()

        # the reading: the number counts with the sweep (past the dial's end, it keeps counting)
        p = du.prog(f, *FILL, vb.ease_in_out_quart)
        dec = du.decimals_of(value)
        shown = du.num(value * p, None if abs(value) >= 1e4 else dec)
        final = du.num(value)
        suffix = data['suffix']
        inner_w = 2 * r_in * 0.78
        num_f = du.fit(final + suffix, lambda z: kit.mono(z, 700, tracking=-0.04), inner_w, round(R * 0.5), 18)
        suf_f = kit.mono(max(14, round(num_f.size * 0.5)), 600)
        nw, sw = text.measure(shown, num_f), text.measure(suffix, suf_f) if suffix else 0
        fw = text.measure(final, num_f)
        nh = text.line_height(num_f)
        x0 = cx - (fw + sw) / 2
        if f >= LAND:
            du.glow(cv, cx, cy, r_in * 0.9, color, 0.18)
        text.draw(cv, [shown], num_f, x0 + fw - nw, cy - nh / 2, kit.INK)
        if suffix:
            text.draw(cv, [suffix], suf_f, x0 + fw + 2, cy - nh / 2 + nh * 0.12, color)
        scale_f = kit.mono(max(13, round(R * 0.075)), 500)
        lo_t, hi_t = ('0', du.num(out_of) + suffix) if out_of > 0 else ('', '')
        by = cy + r_out * math.sin(START) - 4
        text.draw(cv, [lo_t], scale_f, cx + r_in * math.cos(START) - text.measure(lo_t, scale_f) / 2, by,
                  kit.MUTED, alpha=du.prog(f, *RISE))
        text.draw(cv, [hi_t], scale_f, cx - r_in * math.cos(START) - text.measure(hi_t, scale_f) / 2, by,
                  kit.MUTED, alpha=du.prog(f, *RISE))
    cv.mark('dial', *dial)
    cv.mark('reading', x0, cy - nh / 2, fw + sw, nh)

    # ---- caption ----
    k = du.spring(f, CAPTION_AT, CAPTION_SPRING)
    if k <= 0.01:
        return
    if align == 'left':
        lab_lines, lab_f = du.wrap_fit(data['label'], _label_font, cap.w, *sizes['label'])
        blocks = [(lab_lines, lab_f, kit.INK, 'label')]
        if data['detail']:
            det_lines, det_f = du.wrap_fit(data['detail'], _detail_font, cap.w, *sizes['detail'])
            blocks.append((det_lines, det_f, kit.MUTED, 'detail'))
        heights = [text.block_size(b[0], b[1])[1] for b in blocks]
        y = cap.cy - (sum(heights) + 16 * (len(blocks) - 1)) / 2 + 12
        cv.rect(cap.x, y - 24, 56 * min(1.0, k), 5, color, radius=2)
    else:
        lab_lines, lab_f = du.wrap_fit(data['label'], _label_font, cap.w, *sizes['label'])
        blocks = [(lab_lines, lab_f, kit.INK, 'label')]
        if data['detail']:
            det_lines, det_f = du.wrap_fit(data['detail'], _detail_font, cap.w, *sizes['detail'])
            blocks.append((det_lines, det_f, kit.MUTED, 'detail'))
        y = cap.y
    for i, (lines, fnt, col, name) in enumerate(blocks):
        kk = du.spring(f, CAPTION_AT + 5 * i, CAPTION_SPRING)
        dy = 24 * (1 - min(1.0, kk))
        x = cap.x
        box = text.draw(cv, lines, fnt, x, y + dy, col, align=align, width=cap.w if align == 'center' else None,
                        alpha=vb.clamp01(kk * 1.5))
        if kk > 0.01:
            cv.mark(name, *box)
        y += text.block_size(lines, fnt)[1] + (16 if align == 'left' else 12)


COMPONENT = Component(
    id='ring-dial',
    kind='data',
    description=('A gauge dial of radial ticks that light up in a sweep to the reading, the number counting up '
                 'inside and the dial popping as it lands on the beat; a caption beside or below. For one score, '
                 'share or percentage, optionally against a target.'),
    tags=('data', 'gauge', 'ring', 'dial', 'percentage', 'score', 'kpi'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('value', 'number', True, 'The reading, e.g. 72 for 72%.'),
        Slot('out_of', 'number', False, 'The full-dial value; defaults to 100. Use 10 for a score out of 10.'),
        Slot('suffix', 'text', False, 'Unit after the number, e.g. "%" or "/10".', max_length=4),
        Slot('label', 'text', True, 'What the reading is, e.g. "of orders shipped same day".', max_length=40),
        Slot('detail', 'text', False, 'One supporting line under the label.', max_length=72),
        Slot('target', 'number', False, 'A goal on the same scale as value, shown as a notch on the dial.'),
        Slot('color', 'color', False, 'Colour of the lit ticks.'),
    ),
    sample={'value': 87, 'out_of': 100, 'suffix': '%', 'label': 'of orders shipped the same day',
            'detail': 'Up from 61% last spring, past the 80% goal.', 'target': 80, 'color': kit.TEAL},
    draw=draw,
    overlap_ok=(('dial', 'reading'),),
)

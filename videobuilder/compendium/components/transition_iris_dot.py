"""Transition: iris dot. The outgoing title ends on a full stop in the
accent colour that pulses on every beat, throwing a faint ring each time;
then the dot crouches, and the incoming picture grows out of it -- a circle
that swells, drifts to the frame's centre and morphs into the full frame
(`paths.morph`, the shape-morph capability), its rim drawn in the accent.
The picture inside settles from a slight zoom while the outgoing card sinks
back; the incoming title's words then pop in on springs.

Built on the timeline's own `Segment(overlap=...)`, like `overlap_slide`.
"""
import math

import cairo

import videobuilder as vb
from videobuilder import paths, text

from .. import kit
from ..schema import Component, Slot
from . import _transition_util as u

MOVE = 1.25     # beats from the dot's crouch to the full frame
CROUCH = 0.14   # of the move: the dot squashing before it grows
N = 96          # points on the iris outline

GROW = vb.bezier(0.55, 0.0, 0.25, 1.0)


def _fmt(cv):
    return cv.format.name if cv.format else '16x9'


def _from_layout(cv, title):
    """(font, lines, top, dot centre, dot radius) of the outgoing card: the
    title centred, a full stop after its last line."""
    s = kit.safe(cv, 56)
    name = _fmt(cv)
    sizes = {'9x16': (104, 96, 88, 78, 68, 60, 52, 44), '1x1': (84, 76, 68, 60, 52, 46, 40)}.get(
        name, (100, 92, 84, 76, 68, 60, 52, 44))
    lines_max = {'9x16': 4, '1x1': 3}.get(name, 2)
    width = s.w * (0.86 if name == '16x9' else 0.92)
    font, lines = u.fit(title, width, sizes, weight=800, max_lines=lines_max, tracking=-0.03, line_height=1.0)
    lh = text.line_height(font)
    r = font.size * 0.16
    top = s.cy - lh * len(lines) / 2
    last = lines[-1] if lines else ''
    content, baseline = text._content(font)
    base_y = top + (len(lines) - 1) * lh + (lh - content) / 2 + baseline
    last_w = text.measure(last, font)
    # Centre the block (title plus dot) on the frame, so the dot doesn't push it off balance.
    block_w = max([text.measure(ln, font) for ln in lines[:-1]] + [last_w + r * 2.6])
    x0 = s.cx - block_w / 2
    dot = (s.cx - block_w / 2 + (block_w - last_w - r * 2.6) / 2 + last_w + r * 1.6, base_y - r)
    return font, lines, top, x0, block_w, dot, r


def _from_card(cv, data, hold, beat, sink=0.0):
    accent = data['accent']
    cv.fill(kit.BG)
    font, lines, top, x0, block_w, (dx, dy), r = _from_layout(cv, data['from_title'])
    lh = text.line_height(font)
    # A faint ring thrown off the dot on every beat.
    if sink < 0.05:
        for k in (0, 1):
            age = beat + k
            rr = r * (1.6 + 12 * vb.ease_out_expo(vb.clamp01(age / 1.6)))
            a = 0.6 * (1 - vb.clamp01(age / 1.6))
            if (k == 0 or hold > 30) and a > 0.01:
                cv.arc(dx, dy, rr, 0, 2 * math.pi, accent, width=2.5, alpha=a)
    enter = vb.ease_out_quint(vb.clamp01(hold / 14))
    with cv.layer(opacity=enter * (1 - 0.65 * sink), scale=1 - 0.08 * sink, dx=cv.width * 0.04 * sink,
                  dy=cv.height * 0.04 * sink):
        for i, line in enumerate(lines):
            w = text.measure(line, font)
            box = text.draw(cv, [line], font, x0 + (block_w - w) / 2 if i < len(lines) - 1 else
                            x0 + (block_w - (text.measure(lines[-1], font) + r * 2.6)) / 2,
                            top + i * lh + (1 - enter) * 30, kit.INK)
            cv.mark(f'title-from-{i}', *box)
    return (dx, dy), r


def _dot(cv, c, rx, ry, color):
    ctx = cv.ctx
    ctx.save()
    ctx.translate(*c)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill()


def _to_card(cv, data, enter_f, zoom):
    """The incoming card: the picture full-bleed (or the accent, without
    one) under a scrim, its caption and title low on the left."""
    s = kit.safe(cv, 56)
    name = _fmt(cv)
    img = data['to_image']
    frame = vb.Box.of(cv)
    if img is not None:
        u.cover(cv, img, frame, zoom=zoom, focus=(0.4, 0.45))
        ink = kit.INK
        g = cairo.LinearGradient(0, frame.h * 0.3, 0, frame.h)
        g.add_color_stop_rgba(0, *vb.rgba(kit.BG, 0.0))
        g.add_color_stop_rgba(0.55, *vb.rgba(kit.BG, 0.6))
        g.add_color_stop_rgba(1, *vb.rgba(kit.BG, 0.92))
        cv.ctx.rectangle(*frame)
        cv.ctx.set_source(g)
        cv.ctx.fill()
    else:
        cv.fill(data['accent'])
        ink = u.ink_on(data['accent'])
    sizes = {'9x16': (88, 78, 68, 60, 52, 44, 38), '1x1': (68, 60, 52, 46, 40, 34)}.get(
        name, (72, 64, 58, 52, 46, 40, 34))
    width = s.w * (0.66 if name == '16x9' else 1.0)
    font, lines = u.fit(data['to_title'], width, sizes, weight=800, max_lines=3, tracking=-0.03, line_height=1.0)
    lh = text.line_height(font)
    top = s.bottom - lh * len(lines)
    k = 0
    space = text.measure(' ', font)
    for i, line in enumerate(lines):
        x = s.x
        boxes = []
        for word in line.split(' '):
            w = text.measure(word, font)
            t = vb.spring_at(enter_f - 2 * k, 30, **vb.damped(0.45, hz=2.6)) if enter_f - 2 * k > 0 else 0.0
            k += 1
            if t > 0:
                with cv.layer(opacity=vb.clamp01(t * 2)):
                    ctx = cv.ctx
                    ctx.save()
                    cx, cy = x + w / 2, top + i * lh + lh / 2
                    ctx.translate(cx, cy + (1 - t) * 18)
                    sc = 0.55 + 0.45 * t
                    ctx.scale(sc, sc)
                    ctx.translate(-cx, -cy)
                    boxes.append(text.draw(cv, [word], font, x, top + i * lh, ink))
                    ctx.restore()
            x += w + space
        if boxes and enter_f - 2 * k > 20:
            cv.mark(f'title-to-{i}', s.x, top + i * lh, x - space - s.x, lh)
    cap = data['to_caption']
    if cap:
        cf = kit.mono(18, 600, tracking=0.12)
        a = vb.ease_out_quint(vb.clamp01(enter_f / 12))
        cb = text.draw(cv, [cap.upper()], cf, s.x + (1 - a) * -20, top - 44, ink, alpha=a)
        cv.rect(s.x, top - 14, 40 * a, 4, data['accent'])
        if a >= 1:
            cv.mark('caption-to', *cb)


def _circle(cx, cy, r):
    return [(cx + r * math.cos(2 * math.pi * i / N - math.pi / 2), cy + r * math.sin(2 * math.pi * i / N - math.pi / 2))
            for i in range(N)]


def draw(cv, shots):
    data = shots[-1].data
    accent = data['accent']
    on, p, after, fpb = u.phase(shots, MOVE)
    hold = u.hold_f(shots)
    if not on:
        beat = u.beat_frac(shots)
        c, r = _from_card(cv, data, hold, beat)
        s = 1 + 0.35 * math.exp(-beat * 6) * vb.ease_out_quint(vb.clamp01(hold / 14))
        _dot(cv, c, r * s, r * s, accent)
        mark_r = r * 1.35
        cv.mark('dot', c[0] - mark_r, c[1] - mark_r, 2 * mark_r, 2 * mark_r)
        return

    q = vb.clamp01((p - CROUCH) / (1 - CROUCH))
    g = GROW(q)
    if q < 1:   # once the iris fills the frame, the outgoing card is gone
        _from_card(cv, data, 10_000, 0.0, sink=g)
    _, _, _, _, _, (dx, dy), r = _from_layout(cv, data['from_title'])
    if q <= 0:
        # The crouch: a squash before the jump.
        c = vb.ease_out_quint(p / CROUCH)
        _dot(cv, (dx, dy + r * 0.25 * c), r * (1 + 0.35 * c), r * (1 - 0.3 * c), accent)
        return

    W, H = cv.width, cv.height
    reach = math.hypot(W, H) / 2
    m = u.smoothstep((q - 0.35) / 0.65)
    cx, cy = u.lerp(dx, W / 2, u.smoothstep(q / 0.8)), u.lerp(dy, H / 2, u.smoothstep(q / 0.8))
    rad = u.lerp(r * 0.7, reach * 1.02, g)
    pad = 40   # past the frame: resampling the rect cuts its corners, so keep them off screen
    rect = u.rounded_points(-pad, -pad, W + 2 * pad, H + 2 * pad, 40 * (1 - m), per_corner=8)
    shape = paths.morph(_circle(cx, cy, rad), rect, m, closed=True, n=N)

    ctx = cv.ctx
    cv.shape_shadow(shape, dy=10, blur=30, color=(0, 0, 0, 0.55 * (1 - m)))
    ctx.save()
    u.poly(ctx, shape)
    ctx.clip()
    _to_card(cv, data, after + round(0.25 * fpb), zoom=1.22 - 0.22 * vb.ease_out_quint(q))
    ctx.restore()
    rim = 10 * (1 - m) + 2
    if m < 0.98:
        paths.draw(cv, shape, accent, width=rim, closed=True, alpha=1 - m)


COMPONENT = Component(
    id='iris-dot',
    kind='transition',
    description='The outgoing title ends on an accent full stop that pulses on the beat; the dot then grows into '
                'the incoming picture, a circle that morphs into the full frame, and the new title pops in word '
                'by word.',
    tags=('transition', 'iris', 'reveal', 'morph', 'photo', 'beat'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 8),
    slots=(
        Slot('from_title', 'text', True, 'Title on the outgoing card; it ends on the dot, so leave off the full '
             'stop.', max_length=32),
        Slot('to_title', 'text', True, 'Title over the incoming picture, a few words.', max_length=32),
        Slot('to_image', 'image', False, 'The incoming picture, shown full-bleed; without one the accent fills '
             'the frame.'),
        Slot('to_caption', 'text', False, 'Tiny label above the incoming title, e.g. a place or a section.',
             max_length=24),
        Slot('accent', 'color', False, 'The dot and the iris rim.'),
    ),
    sample={
        'from_title': 'It starts with one small point',
        'to_title': 'Then the whole view opens',
        'to_image': u.night_photo(),
        'to_caption': 'Harbour at dusk',
        'accent': kit.ACCENT,
    },
    draw=draw,
)

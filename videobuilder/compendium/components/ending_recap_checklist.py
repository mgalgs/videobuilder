"""Ending: recap checklist. A torn notepad page slaps down on the dark
background, stop-motion style, on twos. Its three takeaways tick off one per
beat: a hand-drawn check strokes on in red, the box hops and the line turns
from pencil grey to ink. Then the closing line lands beside the page and a
marker underline draws itself under it.

Built from `examples/capabilities/paper-collage.py` (paper grain, torn edge,
moving on twos) and `drawn-on-diagram.py` (strokes revealed along their
length, with a hand jitter).
"""
import math
import random

import cairo

import videobuilder as vb
from videobuilder import paths, text

from .. import kit
from ..schema import Component, Slot
from . import _ending_util as u

PAPER_INK = '#1d1b18'
PENCIL = '#9a9388'
RULE = '#9fb3c8'

# Per format: page box (x, y-anchor share, width), item size, closing sizes/lines, closing beside the page or below.
LAYOUT = {
    '16x9': dict(page_w=500, item=(30, 28, 26, 23), close=(64, 56, 48, 40, 34), close_lines=4, beside=True,
                 tilt=-1.6, box=30, gap=24, pad=34, head=17),
    '9x16': dict(page_w=464, item=(36, 33, 30, 27, 25), close=(72, 64, 56, 48, 40), close_lines=3, beside=False,
                 tilt=-1.2, box=34, gap=40, pad=40, head=19),
    '1x1': dict(page_w=456, item=(27, 25, 23, 21, 19), close=(46, 40, 34, 30, 26), close_lines=2, beside=False,
                tilt=-1.0, box=25, gap=16, pad=26, head=15),
}


def _step(f):
    return f - f % 2  # paper moves on twos


def _page_pts(x, y, w, h, seed):
    """A notepad page: three clean edges and a torn top, as a closed point list."""
    rnd = random.Random(seed)
    top = []
    n = 40
    for i in range(n + 1):
        t = i / n
        top.append((x + w * t, y + rnd.uniform(-3.5, 3.5) + 2.5 * math.sin(t * 17)))
    return top + [(x + w, y + h), (x, y + h)]


def _box_pts(x, y, s, seed):
    sq = paths.resample([(x, y), (x + s, y), (x + s, y + s), (x, y + s)], 28, closed=True)
    return paths.jitter(sq, seed=seed, amount=1.1)


def _tick_pts(x, y, s, seed):
    pts = [(x + s * 0.12, y + s * 0.5), (x + s * 0.42, y + s * 0.84), (x + s * 1.05, y - s * 0.22)]
    return paths.jitter(paths.resample(pts, 24), seed=seed, amount=0.7)


def _grain(cv, alpha, seed):
    ctx = cv.ctx
    ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=seed))
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)


def draw(cv, shot):
    cv.fill(kit.BG)
    data, f = shot.data, shot.f
    name = cv.format.name if cv.format is not None and cv.format.name in LAYOUT else '16x9'
    L = LAYOUT[name]
    accent, paper = data['accent'], data['paper']
    beat = u.fpb(shot)
    W, H = cv.width, cv.height
    s = vb.Box.of(cv).pad(48)

    # ---- measure the page ----
    pad, bs, gap = L['pad'], L['box'], L['gap']
    margin = pad + 22  # the red margin line sits in this gutter
    pw = L['page_w'] if L['beside'] else min(L['page_w'], s.w + 8)
    text_w = pw - margin - bs - 16 - pad
    items = [data['point1'], data['point2'], data['point3']]
    item_f = None
    for size in L['item']:
        item_f = kit.font(size, 650)
        wrapped = [text.wrap(t, item_f, text_w) for t in items]
        if all(len(w) <= 2 for w in wrapped):
            break
    item_lh = text.line_height(item_f)
    heights = [max(bs, len(w) * item_lh) for w in wrapped]
    head = data['heading'].upper()
    head_f = kit.mono(L['head'], 600, tracking=0.16)
    head_h = text.line_height(head_f) + gap if head else 0
    ph = pad + head_h + sum(heights) + gap * 2 + pad

    close_w = (s.right - (s.x + pw + 48)) if L['beside'] else s.w
    close_f, close_lines, cw, ch = u.fit(data['closing'], L['close'], 800, close_w, L['close_lines'],
                                         tracking=-0.02)

    if L['beside']:
        px, py = s.x, s.y + (s.h - ph) / 2
        cx, cy = px + pw + 48, s.cy - ch / 2
    else:
        block = ph + 44 + ch + 14
        top = s.y + (s.h - block) * (0.40 if H > W else 0.5)
        px, py = s.cx - pw / 2, top
        cx, cy = s.x + (s.w - cw) / 2 if H <= W else s.x + 8, top + ph + 44

    # ---- the page slaps down, on twos ----
    fs = _step(f)
    p = u.spring(fs, 0.55, 2.2)
    drop = (1 - p) * (H * 0.9)
    rot = math.radians(L['tilt'] + (1 - p) * 9)
    ocx, ocy = px + pw / 2, py + ph / 2
    ctx = cv.ctx
    ctx.save()
    ctx.translate(ocx, ocy + drop)
    ctx.rotate(rot)
    ctx.translate(-ocx, -ocy)

    pts = _page_pts(px, py, pw, ph, seed=7)
    cv.shape_shadow(pts, dx=4, dy=10 + 14 * (1 - p), blur=18, color=(0, 0, 0, 0.55))
    u.poly(ctx, pts)
    ctx.set_source_rgba(*vb.rgba(paper))
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    for k in range(int(ph // item_lh) + 1):  # notepad rules, faint
        ry = py + pad + head_h + item_lh - 2 + k * item_lh
        if ry < py + ph - 8:
            cv.line(px, ry, px + pw, ry, RULE, width=1, alpha=0.35)
    cv.line(px + pad + 6, py, px + pad + 6, py + ph, accent, width=1.5, alpha=0.45)
    _grain(cv, 0.5, seed=2)
    ctx.restore()

    y = py + pad
    tx = px + margin + bs + 16
    if head:
        text.draw(cv, [head], head_f, px + margin, y, PENCIL)
        cv.mark('heading', px + margin, y, text.measure(head, head_f), text.line_height(head_f))
        y += head_h
    for i, (lines, hgt) in enumerate(zip(wrapped, heights)):
        at = beat * (1 + i)
        bx, by = px + margin, y + (min(item_lh, hgt) - bs) / 2
        # The box hops a little when its tick lands.
        hop = 0.0
        if f >= at:
            hop = (1 - u.spring(f - at, 0.35, 3.2)) * 0.18
        sc = 1 + hop
        bcx, bcy = bx + bs / 2, by + bs / 2
        with cv.layer(dx=bcx * (1 - sc), dy=bcy * (1 - sc), scale=sc):
            paths.draw(cv, _box_pts(bx, by, bs, seed=11 + i), PAPER_INK, width=2.2, closed=True)
            tp = vb.clamp01((f - at + 1) / 6)
            if tp > 0:
                tick = paths.reveal(_tick_pts(bx, by, bs, seed=21 + i), u.smoother(tp))
                if len(tick) > 1:
                    ctx.save()
                    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    paths.draw(cv, tick, accent, width=bs * 0.17)
                    ctx.restore()
        ink = vb.clamp01((f - at) / 5)
        color = kit.mix(PENCIL, PAPER_INK, ink)
        box = text.draw(cv, lines, item_f, tx, y, color)
        cv.mark(f'point-{i + 1}', *box)
        y += hgt + gap
    ctx.restore()

    # ---- the closing line, and its marker underline ----
    at = beat * 4
    q = u.spring(f - at, 0.7, 2.2)
    if q > 0.001:
        align = 'center' if (H <= W and not L['beside']) else 'left'
        with cv.layer(opacity=vb.clamp01(q * 1.5), dy=(1 - q) * 24):
            text.draw(cv, close_lines, close_f, cx, cy, kit.INK, align=align, width=cw)
        last_w = text.measure(close_lines[-1], close_f)
        ux0 = cx + ((cw - last_w) / 2 if align == 'center' else 0)
        uy = cy + ch + 6
        under = paths.jitter(paths.resample([(ux0 - 4, uy + 3), (ux0 + last_w + 6, uy - 2)], 30), seed=5,
                             amount=1.2)
        up = u.smoother((f - at - beat * 0.5) / (beat * 0.6))
        seg = paths.reveal(under, up)
        if len(seg) > 1:
            ctx.save()
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            paths.draw(cv, seg, accent, width=7, alpha=0.9)
            ctx.restore()
    cv.mark('closing', cx, cy, cw, ch + 12)


COMPONENT = Component(
    id='recap-checklist',
    kind='ending',
    description=('A recap: a torn notepad page slaps down and three takeaways tick off one per beat with hand-drawn '
                 'red checks, then a closing line lands beside it with a marker underline.'),
    tags=('ending', 'recap', 'summary', 'checklist', 'takeaways', 'paper', 'outro'),
    formats=('16x9', '9x16', '1x1'),
    beats=(8, 16),
    slots=(
        Slot('point1', 'text', True, 'First takeaway, a short phrase, e.g. "Write the script first".', max_length=42),
        Slot('point2', 'text', True, 'Second takeaway, a short phrase.', max_length=42),
        Slot('point3', 'text', True, 'Third takeaway, a short phrase.', max_length=42),
        Slot('closing', 'text', True, 'The closing line after the list, e.g. "Now go make one".', max_length=40),
        Slot('heading', 'text', False, 'A tiny label at the top of the page, shown in capitals, e.g. "In short".',
             max_length=24),
        Slot('accent', 'color', False, 'Colour of the checks, the margin line and the underline.'),
        Slot('paper', 'color', False, 'Colour of the page; keep it light so the dark text reads.'),
    ),
    sample={'point1': 'Plan the story on one page', 'point2': 'Shoot less, cut sooner',
           'point3': 'Land every move on the beat', 'closing': 'Now go make yours', 'heading': 'Three things',
           'accent': kit.ACCENT, 'paper': '#efebe3'},
    draw=draw,
)

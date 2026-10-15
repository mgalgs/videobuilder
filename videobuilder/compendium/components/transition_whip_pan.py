"""Transition: whip pan. Two comic-print panels -- flat colour, a halftone
shadow, heavy type with a misregistered offset, a tag that pops on every
beat -- sit side by side on one long strip (stacked, on 9:16, so the pan
runs up the tall frame). On the beat the camera whips across to the next
one: the strip accelerates hard, smeared by a trail of offset, fading
copies of itself and raked with speed lines, then overshoots and settles.

Built on the timeline's own `Segment(overlap=...)`, like `overlap_slide`.
"""
import math
import random

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _transition_util as u

MOVE = 0.75          # beats the whip takes, overshoot included
COPIES = 7           # smear copies at full speed
OVERSHOOT = 0.045    # of the frame, past the incoming panel before it settles

WHIP = vb.bezier(0.8, 0.0, 0.2, 1.0)


def _tall(cv):
    return (cv.format.name if cv.format else '16x9') == '9x16'


def _panel(cv, data, side, beat, marks):
    """One full-frame panel at the origin."""
    W, H = cv.width, cv.height
    color = data[f'{side}_color']
    ink = kit.BG if u.is_light(color) else kit.INK
    shade = kit.mix(color, kit.BG, 0.38)
    cv.rect(0, 0, W, H, color)
    ctx = cv.ctx
    # A halftone shadow across one corner, and a big disc behind the type.
    ctx.save()
    flip = side == 'to'
    pts = [(W, H * 0.25), (W, H), (W * 0.2, H)] if not flip else [(0, 0), (W * 0.8, 0), (0, H * 0.75)]
    u.poly(ctx, pts)
    ctx.clip()
    ctx.set_source(vb.halftone_pattern(12, 3.6, angle=0.5, color=shade))
    ctx.paint()
    ctx.restore()
    s = kit.safe(cv, 56)
    tall = _tall(cv)
    name = cv.format.name if cv.format else '16x9'
    disc_r = min(W, H) * (0.36 if tall else 0.42)
    dcx = W * (0.68 if not flip else 0.32) if not tall else W * 0.5
    dcy = H * 0.5 if not tall else H * (0.3 if not flip else 0.34)
    cv.ctx.arc(dcx, dcy, disc_r, 0, 2 * math.pi)
    ctx.set_source_rgba(*vb.rgba(kit.mix(color, kit.INK, 0.22)))
    ctx.fill()

    sizes = {'9x16': (120, 108, 96, 84, 74, 64, 56, 48), '1x1': (96, 86, 76, 68, 60, 52, 44)}.get(
        name, (112, 100, 90, 80, 70, 62, 54, 46))
    width = s.w * (0.8 if name == '16x9' else 1.0)
    lines_max = {'9x16': 4, '1x1': 3}.get(name, 2)
    title_f, lines = u.fit(data[f'{side}_title'], width, sizes, weight=900, max_lines=lines_max, tracking=-0.04,
                           line_height=0.94, max_height=s.h - 90)
    lh = text.line_height(title_f)
    block = lh * len(lines)
    top = s.cy - block / 2 + 30 if not tall else s.bottom - block - 20
    off = max(4, title_f.size * 0.06)
    shadow = kit.INK if ink == kit.BG else kit.BG
    for i, line in enumerate(lines):
        text.draw(cv, [line], title_f, s.x + off, top + i * lh + off, shadow)
        box = text.draw(cv, [line], title_f, s.x, top + i * lh, ink)
        if marks:
            cv.mark(f'title-{side}-{i}', *box)

    tag = data[f'{side}_tag']
    if tag:
        tf = kit.mono(20, 700, tracking=0.1)
        tb = text.box(tag.upper(), tf, padding=(8, 14))
        tx, ty = s.x, top - tb.h - 26
        pop = 1 + 0.14 * math.exp(-beat * 9)
        ctx.save()
        ctx.translate(tx + tb.w / 2, ty + tb.h / 2)
        ctx.rotate(math.radians(-4 if not flip else 3))
        ctx.scale(pop, pop)
        ctx.translate(-tb.w / 2, -tb.h / 2)
        cv.rect(4, 4, tb.w, tb.h, kit.BG)
        cv.rect(0, 0, tb.w, tb.h, kit.INK)
        text.draw_in(cv, vb.Box(0, 0, tb.w, tb.h), tag.upper(), tf, kit.BG, padding=(8, 14))
        if marks:
            cv.mark(f'tag-{side}', 0, 0, tb.w, tb.h)
        ctx.restore()


def _strip(cv, data, pos, beat, marks):
    """Both panels on one strip, scrolled by `pos` (0: the outgoing panel in
    frame, 1: the incoming one)."""
    tall = _tall(cv)
    span = cv.height if tall else cv.width
    shift = -pos * span
    # Past either end, the strip runs on in that panel's colour, so an overshoot never shows a gap.
    for o, side in ((shift - span, 'from'), (shift + 2 * span, 'to')):
        if -span < o < span:
            cv.rect(0 if tall else o, o if tall else 0, cv.width, cv.height, data[f'{side}_color'])
    for k, side in enumerate(('from', 'to')):
        o = shift + k * span
        if o <= -span or o >= span:
            continue
        with cv.layer(dx=0 if tall else o, dy=o if tall else 0):
            _panel(cv, data, side, beat, marks and abs(o) < 0.5)


def _speed_lines(cv, v, tall, seed):
    if v < 0.05:
        return
    rnd = random.Random(seed)
    W, H = cv.width, cv.height
    along, across = (H, W) if tall else (W, H)
    for _ in range(28):
        c = rnd.uniform(0, across)
        a0 = rnd.uniform(-0.2, 1.0) * along
        ln = along * rnd.uniform(0.25, 0.7) * v
        w = rnd.uniform(1.5, 5)
        alpha = min(1.0, v) * rnd.uniform(0.25, 0.7)
        if tall:
            cv.line(c, a0, c, a0 + ln, kit.INK, width=w, alpha=alpha)
        else:
            cv.line(a0, c, a0 + ln, c, kit.INK, width=w, alpha=alpha)


def _pos(f, dur, fpb):
    """Strip position `f` frames into the move: the whip, past the panel by
    OVERSHOOT, then a damped settle back onto it."""
    if f < dur:
        return WHIP(f / dur) * (1 + OVERSHOOT)
    t = (f - dur) / fpb
    return 1 + OVERSHOOT * math.exp(-t * 7) * math.cos(t * 13)


def draw(cv, shots):
    data = shots[-1].data
    on, p, after, fpb = u.phase(shots, MOVE)
    beat = u.beat_frac(shots)
    tall = _tall(cv)
    if not on:
        enter = vb.ease_out_quint(vb.clamp01(u.hold_f(shots) / 12))
        _strip(cv, data, -0.12 * (1 - enter), beat, True)
        return
    dur = MOVE * fpb
    f = p * dur + max(0, after)
    pos = _pos(f, dur, fpb)
    v = abs(pos - _pos(max(0.0, f - 1), dur, fpb))   # frame widths moved since the last frame
    speed = vb.clamp01(v / 0.16)
    cv.fill(kit.BG)
    _strip(cv, data, pos, beat if after > 0 else 0.5, after > 0)
    # The smear: copies trailing back along the move, fainter the further back.
    n = round(COPIES * speed)
    for i in range(1, n + 1):
        with cv.layer(opacity=0.42 * (1 - i / (n + 1))):
            _strip(cv, data, pos - v * 1.6 * i / n, 0.5, False)
    _speed_lines(cv, speed, tall, seed=int(f))


COMPONENT = Component(
    id='whip-pan',
    kind='transition',
    description='Two comic-print panels (flat colour, halftone shadow, heavy offset type, a tag that pops on the '
                'beat) on one strip; on the beat the camera whips to the next with a motion smear and speed lines, '
                'overshoots and settles. Pans up the tall frame on 9:16.',
    tags=('transition', 'whip', 'pan', 'smear', 'comic', 'halftone', 'energy'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 8),
    slots=(
        Slot('from_title', 'text', True, 'Big title on the outgoing panel, a few punchy words.', max_length=28),
        Slot('to_title', 'text', True, 'Big title on the incoming panel, a few punchy words.', max_length=28),
        Slot('from_tag', 'text', False, 'A one- or two-word tag above the outgoing title.', max_length=14),
        Slot('to_tag', 'text', False, 'A one- or two-word tag above the incoming title.', max_length=14),
        Slot('from_color', 'color', False, 'Flat colour of the outgoing panel; pick a mid or light tone.'),
        Slot('to_color', 'color', False, 'Flat colour of the incoming panel; contrast it with the first.'),
    ),
    sample={
        'from_title': 'Monday was slow',
        'to_title': 'Friday went fast',
        'from_tag': 'Before',
        'to_tag': 'After',
        'from_color': kit.TEAL,
        'to_color': kit.ACCENT,
    },
    draw=draw,
)

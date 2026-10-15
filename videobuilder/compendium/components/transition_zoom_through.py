"""Transition: zoom through. The outgoing card is a viewfinder -- corner
brackets that tighten on every beat, a mono zoom readout, one giant word --
and on the beat the camera punches through it: the card scales past the
lens, accelerating, smeared by a trail of fading copies (a zoom blur drawn
in code) and streaked by light, while the readout races up. Out of the
rush the incoming card arrives from slightly small on a spring, its corners
squaring off as it lands: a framed picture with its title beside it (16:9)
or under it (9:16, 1:1).

Built on the timeline's own `Segment(overlap=...)`, like `overlap_slide`.
"""
import math
import random

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _transition_util as u

MOVE = 1.0          # beats: the punch through, and the incoming card's arrival
OUT_END = 0.62      # of the move: the outgoing card is past the lens
IN_START = 0.3      # of the move: the incoming card appears
ZOOM_MAX = 9.0
ECHOES = 6
PAGE = '#1b1d24'    # the incoming card, a step lighter than the outgoing one

RUSH = vb.bezier(0.7, 0.0, 0.95, 0.6)   # accelerating into the lens


def _fmt(cv):
    return cv.format.name if cv.format else '16x9'


# ---- the outgoing viewfinder ----

def _brackets(cv, s, inset, color, alpha):
    arm = 34
    for (x, y, sx, sy) in ((s.x, s.y, 1, 1), (s.right, s.y, -1, 1), (s.x, s.bottom, 1, -1), (s.right, s.bottom, -1, -1)):
        x, y = x + sx * inset, y + sy * inset
        cv.line(x, y, x + sx * arm, y, color, width=4, alpha=alpha)
        cv.line(x, y, x, y + sy * arm, color, width=4, alpha=alpha)


def _ruler(cv, s, zoom, accent, alpha, marks):
    """A lens scale along the bottom (or, on 9:16, up the right side): fine
    ticks, with an accent needle and the zoom readout at the current zoom."""
    tall = _fmt(cv) == '9x16'
    a0, a1 = (s.bottom - 64, s.y + 64) if tall else (s.x + 64, s.right - 64)
    edge = s.right - 6 if tall else s.bottom - 6
    n = 40
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        ln = 16 if i % 5 == 0 else 8
        if tall:
            cv.line(edge, t, edge - ln, t, kit.MUTED, width=2, alpha=alpha * 0.7)
        else:
            cv.line(t, edge, t, edge - ln, kit.MUTED, width=2, alpha=alpha * 0.7)
    k = vb.clamp01(math.log(max(1.0, zoom)) / math.log(ZOOM_MAX))
    t = a0 + (a1 - a0) * k
    mf = kit.mono(18, 600, tracking=0.06)
    readout = f'{zoom:.1f}\u00d7'
    rw, rh = text.measure(readout, mf), text.line_height(mf)
    if tall:
        cv.line(edge + 4, t, edge - 30, t, accent, width=4, alpha=alpha)
        rb = text.draw(cv, [readout], mf, edge - 42 - rw, t - rh / 2, accent, alpha=alpha)
    else:
        cv.line(t, edge + 4, t, edge - 30, accent, width=4, alpha=alpha)
        rb = text.draw(cv, [readout], mf, t - rw / 2, edge - 36 - rh, accent, alpha=alpha)
    if marks:
        cv.mark('readout', *rb)


def _from_content(cv, data, enter, beat, zoom, marks=True):
    s = kit.safe(cv, 48)
    name = _fmt(cv)
    accent = data['accent']
    pulse = math.exp(-beat * 7)
    _brackets(cv, s, 10 * pulse, kit.INK, 0.75)
    _ruler(cv, s, zoom, accent, enter, marks)
    sizes = {'9x16': (190, 170, 150, 132, 116, 100, 88, 76, 64), '1x1': (170, 150, 132, 116, 100, 88, 76, 64)}.get(
        name, (220, 196, 176, 156, 136, 118, 100, 88, 76))
    lines_max = {'9x16': 3, '1x1': 2}.get(name, 2)
    inner = s.pad(70, 52, 70, 4) if name == '9x16' else s.pad(40, 40)
    font, lines = u.fit(data['from_title'], inner.w, sizes, weight=900, max_lines=lines_max, tracking=-0.05,
                        line_height=0.92, max_height=s.h - 2 * 64)
    lh = text.line_height(font)
    top = s.cy - lh * len(lines) / 2
    with cv.layer(opacity=enter, dy=(1 - enter) * 40):
        for i, line in enumerate(lines):
            box = text.draw(cv, [line], font, inner.x, top + i * lh, kit.INK, align='center', width=inner.w)
            if marks:
                cv.mark(f'word-{i}', *box)
    mf = kit.mono(18, 600, tracking=0.12)
    kicker = data['from_kicker']
    if kicker:
        kb = text.draw(cv, [kicker.upper()], mf, s.x + 52, s.y + 18, kit.INK, alpha=enter)
        cv.rect(s.x + 52 - 18, s.y + 25, 8, 8, accent, radius=4, alpha=enter * (0.4 + 0.6 * pulse))
        if marks:
            cv.mark('kicker-from', *kb)


def _streaks(cv, speed, color):
    """Light streaking out from the centre, more and longer the faster the rush."""
    if speed <= 0.02:
        return
    cx, cy = cv.width / 2, cv.height / 2
    reach = math.hypot(cx, cy)
    rnd = random.Random(7)
    for _ in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = reach * rnd.uniform(0.18, 0.7)
        ln = reach * rnd.uniform(0.15, 0.5) * speed
        c, sn = math.cos(a), math.sin(a)
        cv.line(cx + c * r0, cy + sn * r0, cx + c * (r0 + ln), cy + sn * (r0 + ln), color,
                width=rnd.uniform(1, 3), alpha=0.5 * speed * rnd.uniform(0.4, 1))


# ---- the incoming card ----

def _to_layout(cv):
    s = kit.safe(cv, 56)
    name = _fmt(cv)
    if name == '16x9':
        pic, col = s.row(1.12 * vb.fr, vb.fr, gap=40)
        return pic, col, (64, 56, 50, 44, 40, 36, 32), 4, 'center'
    if name == '9x16':
        pic, col = s.column(1.5 * vb.fr, vb.fr, gap=44)
        return pic, col, (80, 72, 64, 56, 50, 44, 40, 36), 4, 'top'
    pic, col = s.column(1.45 * vb.fr, vb.fr, gap=28)
    return pic, col, (54, 48, 44, 40, 36, 32), 2, 'top'


def _to_content(cv, data, enter_f, arrive=1.0):
    accent = data['accent']
    cv.fill(PAGE)
    pic, col, sizes, lines_max, valign = _to_layout(cv)
    img = data['to_image']
    with cv.clip(*pic, radius=18):
        if img is not None:
            u.cover(cv, img, pic, zoom=1.08 - 0.08 * vb.ease_out_quint(vb.clamp01(enter_f / 40)))
        else:
            cv.rect(*pic, accent)
            cv.ctx.set_source(vb.halftone_pattern(14, 4, angle=0.4, color=kit.mix(accent, kit.BG, 0.35)))
            cv.ctx.paint()
    cv.mark('picture-to', *pic)
    # The viewfinder's brackets, carried over onto the picture's corners.
    s = kit.safe(cv, 48)
    g = pic.pad(-12)
    t = vb.clamp01(arrive)
    box = vb.Box(u.lerp(s.x, g.x, t), u.lerp(s.y, g.y, t), u.lerp(s.w, g.w, t), u.lerp(s.h, g.h, t))
    _brackets(cv, box, 0, accent, 1.0)
    mf = kit.mono(18, 600, tracking=0.12)
    kicker = data['to_kicker']
    font, lines = u.fit(data['to_title'], col.w, sizes, weight=800, max_lines=lines_max, tracking=-0.03,
                        line_height=1.0)
    lh = text.line_height(font)
    kh = text.line_height(mf) + 18 if kicker else 0
    block = kh + lh * len(lines)
    y = col.y + (col.h - block) / 2 if valign == 'center' else col.y
    if kicker:
        a = vb.ease_out_quint(vb.clamp01(enter_f / 10))
        kb = text.draw(cv, [kicker.upper()], mf, col.x + 20, y, accent, alpha=a)
        cv.rect(col.x, y + 6, 8 * a, 8, accent, radius=4)
        cv.mark('kicker-to', *kb)
        y += kh
    for i, line in enumerate(lines):
        p = vb.ease_out_quint(vb.clamp01((enter_f - 3 - 3 * i) / 14))
        box = text.draw(cv, [line], font, col.x + (1 - p) * 30, y + i * lh, kit.INK, alpha=p)
        if p >= 1:
            cv.mark(f'title-to-{i}', *box)


def _scaled(cv, s, opacity=1.0):
    cx, cy = cv.width / 2, cv.height / 2
    return cv.layer(opacity=opacity, dx=cx - cx * s, dy=cy - cy * s, scale=s)


def draw(cv, shots):
    data = shots[-1].data
    on, p, after, fpb = u.phase(shots, MOVE)
    hold = u.hold_f(shots)
    beat = u.beat_frac(shots)
    cv.fill(kit.BG)
    if not on:
        _from_content(cv, data, vb.ease_out_quint(vb.clamp01(hold / 14)), beat, 1.0)
        return

    dur = MOVE * fpb
    # The incoming card first: the outgoing one rushes past the lens in front of it.
    t_in = p * dur + max(0, after) - IN_START * dur
    if t_in > 0:
        sp = vb.spring_at(t_in, 30, **vb.damped(0.42, hz=1.9))
        s = 0.8 + 0.2 * sp
        settle = vb.clamp01(t_in / (dur * 1.2))
        radius = 44 * (1 - settle)
        frame = vb.Box.of(cv)
        with _scaled(cv, s, opacity=vb.clamp01(t_in / 5)):
            cv.shadow(*frame, radius=radius, dy=24, blur=60, color=(0, 0, 0, 0.6 * (1 - settle)))
            with cv.clip(*frame, radius=radius):
                _to_content(cv, data, t_in - 0.5 * dur, sp)
            if settle < 1:
                cv.outline(*frame, kit.INK, width=2, radius=radius, alpha=0.25 * (1 - settle))

    q = vb.clamp01(p / OUT_END)
    if q < 1:
        k = RUSH(q)
        z = math.exp(math.log(ZOOM_MAX) * k)
        dz = math.log(ZOOM_MAX) * (RUSH(min(1, q + 0.04)) - k) / 0.04   # how fast the zoom is moving
        speed = vb.clamp01(dz / 6)
        fade = 1 - vb.clamp01((q - 0.45) / 0.55)
        # The trail first, faint and smaller (where the card just was), then the card itself.
        for e in range(ECHOES, 0, -1):
            zs = z * math.exp(-0.07 * e * speed * 3)
            with _scaled(cv, zs, opacity=fade * 0.32 * speed * (1 - e / (ECHOES + 1))):
                _from_content(cv, data, 1.0, 0.5, zs, marks=False)
        with _scaled(cv, z, opacity=fade):
            _from_content(cv, data, 1.0, 0.5, z, marks=False)
        _streaks(cv, speed * fade, kit.INK)


COMPONENT = Component(
    id='zoom-through',
    kind='transition',
    description='A viewfinder card with one giant word; on the beat the camera punches through it, with a zoom '
                'blur and light streaks, and the next card (a framed picture with its title) springs in from '
                'slightly small.',
    tags=('transition', 'zoom', 'punch-in', 'camera', 'energy', 'photo'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 8),
    slots=(
        Slot('from_title', 'text', True, 'One or two big words on the outgoing card.', max_length=16),
        Slot('to_title', 'text', True, 'Title beside the incoming picture, a short sentence.', max_length=40),
        Slot('from_kicker', 'text', False, 'Tiny label in the viewfinder\'s top corner.', max_length=24),
        Slot('to_kicker', 'text', False, 'Tiny label above the incoming title.', max_length=24),
        Slot('to_image', 'image', False, 'The incoming picture; without one, an accent halftone panel.'),
        Slot('accent', 'color', False, 'The readout, labels and fallback panel.'),
    ),
    sample={
        'from_title': 'Closer',
        'to_title': 'Every hill has a story to tell',
        'from_kicker': 'Field notes',
        'to_kicker': 'Up close',
        'to_image': kit.sample_photo(),
        'accent': kit.ACCENT,
    },
    draw=draw,
)

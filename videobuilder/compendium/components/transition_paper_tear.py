"""Transition: paper tear. The outgoing card is a printed sheet -- grainy
off-white paper, a kicker over a double rule, a heavy headline, greyed lines
of body copy -- and on the beat it tears in two along a ragged line: the
tear runs from one edge to the other as the halves swing open about its far
end, then they are pulled away out of frame, each casting a lift shadow and
showing a pale fibrous rim where it tore. Underneath is coloured paper with
the picture slapped on and taped down, and the title on a torn scrap. Paper
moves in stop-motion, on twos.

The tear runs the short way across the frame: top to bottom on 16:9 and
1:1, side to side on 9:16, so the halves are wide pieces on every format.

Built on the timeline's own `Segment(overlap=...)`, like `overlap_slide`;
the look after `examples/capabilities/paper-collage.py`.
"""
import math
import random
from functools import lru_cache

import cairo

import videobuilder as vb
from videobuilder import paths, text

from .. import kit
from ..schema import Component, Slot
from . import _transition_util as u

SHEET = '#ece6da'
RIM = '#fbf8f1'
INK = '#1b1916'
COPY = '#c9c1b3'     # the greyed body-copy lines

MOVE = 1.5           # beats: the tear opening, then the halves pulled away
OPEN = 0.32          # of the move: the tear running across


def _fmt(cv):
    return cv.format.name if cv.format else '16x9'


def step(f):
    """Stop-motion: paper only moves on even frames."""
    return f - f % 2


def grain(cv, alpha, seed=1):
    ctx = cv.ctx
    ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=seed))
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)


# ---- the tear's geometry, per format ----

@lru_cache(maxsize=8)
def _tear(name, W, H):
    """(tear line, half A, half B, hinge, (sign A, sign B), axis): the ragged
    line, both halves as polygons, the point they swing about, which way
    each turns, and the direction (unit vector) half B is pulled away."""
    m = 40
    if name == '9x16':
        line = [(-m, H * 0.46), (W * 0.35, H * 0.5), (W * 0.7, H * 0.47), (W + m, H * 0.53)]
        t = paths.torn(paths.resample(line, 60), seed=17, amount=14, step=3, closed=False)
        a = t + [(W + m, -m), (-m, -m)]
        b = t + [(W + m, H + m), (-m, H + m)]
        return t, a, b, t[-1], (1, -1), (0.0, 1.0)
    slant = 0.16 if name == '1x1' else 0.06
    line = [(W * (0.5 + slant), -m), (W * (0.5 + slant * 0.2), H * 0.45), (W * (0.5 - slant), H + m)]
    t = paths.torn(paths.resample(line, 60), seed=17, amount=14, step=3, closed=False)
    a = t + [(-m, H + m), (-m, -m)]
    b = t + [(W + m, H + m), (W + m, -m)]
    return t, a, b, t[-1], (-1, 1), (1.0, 0.0)


# ---- the outgoing printed sheet ----

def _sheet(cv, data, enter):
    W, H = cv.width, cv.height
    name = _fmt(cv)
    cv.fill(SHEET)
    grain(cv, 0.55, seed=3)
    s = kit.safe(cv, 56)
    accent = data['paper']
    kicker = data['from_kicker']
    mf = kit.mono(18, 700, tracking=0.16)
    y = s.y
    if kicker:
        kb = text.draw(cv, [kicker.upper()], mf, s.x, y, INK, alpha=enter)
        cv.mark('kicker-from', *kb)
        y += text.line_height(mf) + 10
    cv.rect(s.x, y, s.w * enter, 3, INK)
    cv.rect(s.x, y + 7, s.w * enter, 1.2, INK)
    cv.rect(s.x, y + 16, 44 * enter, 8, accent)
    y += 44
    sizes = {'9x16': (84, 76, 68, 60, 52, 46, 40), '1x1': (72, 64, 56, 50, 44, 38)}.get(
        name, (76, 68, 60, 54, 48, 42, 36))
    lines_max = {'9x16': 5, '1x1': 3}.get(name, 2)
    width = s.w * (0.9 if name == '16x9' else 1.0)
    font, lines = u.fit(data['from_title'], width, sizes, weight=900, max_lines=lines_max, tracking=-0.035,
                        line_height=0.98, balance=False)
    lh = text.line_height(font)
    for i, line in enumerate(lines):
        box = text.draw(cv, [line], font, s.x, y + i * lh, INK, alpha=enter)
        cv.mark(f'title-from-{i}', *box)
    y += lh * len(lines) + 30
    # Greyed lines of body copy, in columns, filling what's left of the sheet.
    cols = 1 if name == '9x16' else 2 if name == '1x1' else 3
    gap = 28
    cw = (s.w - gap * (cols - 1)) / cols
    rnd = random.Random(5)
    for c in range(cols):
        yy = y
        x = s.x + c * (cw + gap)
        while yy + 10 <= s.bottom:
            ln = cw * (rnd.uniform(0.55, 0.95) if rnd.random() < 0.18 else 1.0)
            cv.rect(x, yy, ln * enter, 8, COPY, radius=4)
            yy += 19
    grain(cv, 0.25, seed=4)


# ---- the incoming collage ----

def _collage_layout(cv):
    s = kit.safe(cv, 56)
    name = _fmt(cv)
    if name == '16x9':
        pic, col = s.row(1.05 * vb.fr, vb.fr, gap=44)
        return pic.pad(10, 6), col, (76, 68, 60, 54, 48, 42, 38, 34)
    if name == '9x16':
        pic, col = s.column(1.1 * vb.fr, vb.fr, gap=48)
        return pic.pad(6, 10), col, (88, 80, 72, 64, 56, 50, 44, 38)
    pic, col = s.column(1.3 * vb.fr, vb.fr, gap=36)
    return pic.pad(0, 30), col, (60, 54, 48, 42, 38, 34)


def _tape(cv, cx, cy, ang, seed):
    pts = paths.torn([(-48, -14), (48, -14), (48, 14), (-48, 14)], seed=seed, amount=2.0, step=2)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    cv.shape_shadow(pts, dx=1, dy=2, blur=4, color=(40, 10, 0, 0.25))
    u.poly(ctx, pts)
    ctx.set_source_rgba(*vb.rgba('#efe9da', 0.85))
    ctx.fill()
    ctx.restore()


def _collage(cv, data, f, fpb):
    """The incoming card, `f` frames after the move began (stop-motion)."""
    paper = data['paper']
    cv.fill(paper)
    grain(cv, 0.45, seed=2)
    pic, col, sizes = _collage_layout(cv)
    img = data['to_image']
    ctx = cv.ctx
    land = step(f) - round(MOVE * fpb * 0.55)   # the picture slaps down as the halves clear
    t = vb.ease_out_back(vb.clamp01(land / 8)) if land > 0 else 0.0
    if t > 0:
        border = 10
        ang = math.radians(-2.5) + (1 - t) * math.radians(-8)
        sc = 1 + (1 - t) * 0.25
        ctx.save()
        ctx.translate(pic.cx, pic.cy)
        ctx.rotate(ang)
        ctx.scale(sc, sc)
        ctx.translate(-pic.cx, -pic.cy)
        lift = 6 + (1 - t) * 24
        frame_pts = u.rounded_points(*pic, 3, per_corner=2)
        cv.shape_shadow(frame_pts, dx=lift * 0.4, dy=lift, blur=12 + lift, color=(50, 10, 0, 0.45))
        cv.rect(*pic, RIM, radius=3)
        inner = pic.pad(border)
        if img is not None:
            with cv.clip(*inner):
                u.cover(cv, img, inner)
        else:
            cv.rect(*inner, INK)
            with cv.clip(*inner):
                ctx.set_source(vb.halftone_pattern(12, 3.4, angle=0.6, color=kit.mix(paper, INK, 0.45)))
                ctx.paint()
        with cv.clip(*pic):
            grain(cv, 0.3, seed=6)
        ctx.restore()
        cv.mark('picture-to', *pic)
        if land >= 10:
            _tape(cv, pic.x + 26, pic.y + 14, math.radians(-36), 81)
        if land >= 14:
            _tape(cv, pic.right - 24, pic.bottom - 16, math.radians(-32), 82)

    # The title on a torn scrap.
    sl = step(f) - round(MOVE * fpb * 0.55) - 6
    if sl > 0:
        ts = vb.ease_out_back(vb.clamp01(sl / 8))
        font, lines = u.fit(data['to_title'], col.w - 44, sizes, weight=900, max_lines=4, tracking=-0.03,
                            line_height=1.0)
        lh = text.line_height(font)
        bw = max(text.measure(ln, font) for ln in lines) + 44
        bh = lh * len(lines) + 36
        bx = col.x
        by = col.y + (col.h - bh) / 2
        scrap = paths.torn(u.rounded_points(bx, by, bw, bh, 0, per_corner=1), seed=9, amount=5, step=2.5)
        ctx.save()
        ctx.translate(bx + bw / 2, by + bh / 2 - (1 - ts) * 40)
        ctx.rotate(math.radians(1.8) + (1 - ts) * math.radians(6))
        ctx.translate(-(bx + bw / 2), -(by + bh / 2))
        cv.shape_shadow(scrap, dx=3, dy=6, blur=12, color=(50, 10, 0, 0.4))
        u.poly(ctx, scrap)
        ctx.set_source_rgba(*vb.rgba(SHEET))
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        grain(cv, 0.5, seed=7)
        ctx.restore()
        ctx.new_path()
        tb = text.draw(cv, list(lines), font, bx + 22, by + 18, INK)
        if sl >= 8:
            cv.mark('title-to', *tb)
        ctx.restore()


# ---- the tear ----

def _half(cv, data, poly, rim_line, hinge, angle, dx, dy, lift):
    ctx = cv.ctx
    ctx.save()
    ctx.translate(dx, dy)
    ctx.translate(*hinge)
    ctx.rotate(angle)
    ctx.translate(-hinge[0], -hinge[1])
    cv.shape_shadow(poly, dx=lift * 0.4, dy=lift, blur=10 + lift * 1.5, color=(40, 20, 5, 0.5))
    ctx.save()
    u.poly(ctx, poly)
    ctx.clip()
    _sheet(cv, data, 1.0)
    ctx.restore()
    # The torn edge: the paper's pale core showing, fuzzy with fibre.
    paths.draw(cv, rim_line, RIM, width=5)
    paths.draw(cv, paths.jitter(rim_line, seed=3, amount=1.6, wander=0.8), '#ffffff', width=1.6, alpha=0.8)
    ctx.restore()


def draw(cv, shots):
    data = shots[-1].data
    on, p, after, fpb = u.phase(shots, MOVE)
    if not on:
        hold = u.hold_f(shots)
        _sheet(cv, data, vb.ease_out_quint(vb.clamp01(hold / 16)))
        return

    dur = MOVE * fpb
    f = p * dur + max(0, after)
    W, H = cv.width, cv.height
    line, a, b, hinge, (sa, sb), (ax, ay) = _tear(_fmt(cv), W, H)
    tf = step(f) / dur
    _collage(cv, data, f, fpb)
    if tf >= 1:
        return
    o = u.smoothstep(tf / OPEN)
    pull = vb.clamp01((tf - OPEN * 0.7) / (1 - OPEN * 0.7)) ** 2
    rnd = random.Random(int(step(f)))
    jit = (rnd.uniform(-1, 1) * 1.2, rnd.uniform(-1, 1) * 1.2)
    reach = max(W, H) * 1.1
    for poly, sign, out in ((a, sa, -1), (b, sb, 1)):
        angle = sign * (math.radians(7) * o + math.radians(24) * pull)
        dx = out * ax * reach * pull + jit[0]
        dy = out * ay * reach * pull + H * 0.12 * pull + jit[1]
        _half(cv, data, poly, line, hinge, angle, dx, dy, 4 + 10 * o + 20 * pull)


COMPONENT = Component(
    id='paper-tear',
    kind='transition',
    description='A printed paper sheet (headline over greyed body copy) tears in two on the beat; the halves '
                'swing open and are pulled away, showing coloured paper with the picture taped down and the new '
                'title on a torn scrap. Stop-motion, on twos.',
    tags=('transition', 'paper', 'tear', 'collage', 'tactile', 'photo'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 4),
    slots=(
        Slot('from_title', 'text', True, 'Headline printed on the outgoing sheet.', max_length=36),
        Slot('to_title', 'text', True, 'Title on the torn scrap of the incoming card, a few words.', max_length=32),
        Slot('from_kicker', 'text', False, 'Tiny masthead label above the headline.', max_length=24),
        Slot('to_image', 'image', False, 'The picture taped onto the incoming card; without one, a halftone '
             'panel.'),
        Slot('paper', 'color', False, 'Colour of the paper underneath; a strong mid tone works best.'),
    ),
    sample={
        'from_title': 'The old plan, in print',
        'to_title': 'The new one, by hand',
        'from_kicker': 'Morning edition',
        'to_image': kit.sample_photo(),
        'paper': '#c75431',
    },
    draw=draw,
)

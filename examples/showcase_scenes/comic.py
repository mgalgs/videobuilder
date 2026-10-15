"""Comic-book halftone, three panels cut on the beat: Lumi at Lumen HQ with
the plan, an extreme close-up, and the launch burst. Flat inks, thick
outlines and Ben-Day dots, in the look's own palette (STYLE.md's style-card
exception)."""
import math

import cairo

import videobuilder as vb
from videobuilder import Box, text

from . import kit
from .kit import pick, rounded_points

PAPER, CINK, RED, BLUE, YELLOW, SKIN = '#f4ecd8', '#15120f', '#c81e3a', '#2e6f9e', '#f0a202', '#ef5b4c'
PERIOD = 45


def _dots(cv, pitch, radius, colour, angle=0.5, alpha=1.0, dx=0.0, dy=0.0):
    ctx = cv.ctx
    ctx.save()
    ctx.translate(dx, dy)
    ctx.set_source(vb.halftone_pattern(pitch, radius, angle=angle, color=colour))
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def _panel(cv, st, ground, dots=None):
    """The page and one panel filling the content box; returns the panel box."""
    cv.fill(PAPER)
    panel = st.content.pad(6)
    with cv.clip(*panel):
        cv.rect(*panel, ground)
        if dots:
            _dots(cv, *dots)
    cv.outline(*panel, CINK, width=8)
    return panel


def _caption(cv, panel, copy, size, at='top'):
    f = kit.font(size, 850, tracking=0.02)
    lines, (w, h) = kit.lines_of(copy, f, panel.w - 80)
    cb = Box(panel.x + 4, panel.y + 4 if at == 'top' else panel.bottom - h - 28, w + 40, h + 24)
    cv.rect(*cb, YELLOW)
    cv.outline(*cb, CINK, width=5)
    text.draw(cv, lines, f, cb.x + 20, cb.y + 12, CINK)
    cv.mark('caption', *cb)
    return cb


def _ink_poly(cv, pts, fill, width=8):
    ctx = cv.ctx
    kit.poly(ctx, pts)
    ctx.set_source_rgba(*vb.rgba(fill))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(CINK))
    ctx.set_line_width(width)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def _lumi(cv, cx, foot, size, squint=False, blink=False, name='lumi'):
    """Lumi in ink: flat red, a halftone shadow down its right side, thick outline."""
    w, h = size, size * 1.05
    x, y = cx - w / 2, foot - h
    ctx = cv.ctx
    cv.rect(x, y, w, h, SKIN, radius=w / 2)
    ctx.save()
    kit.poly(ctx, rounded_points(x, y, w, h, w / 2 - 0.01))
    ctx.clip()
    ctx.new_path()
    ctx.rectangle(cx + w * 0.12, y, w, h)
    ctx.clip()
    _dots(cv, 11, 3.6, RED, alpha=0.9)
    ctx.restore()
    cv.outline(x, y, w, h, CINK, width=8, radius=w / 2)
    er = w * 0.085
    for ex in (-0.18, 0.18):
        ehx, ehy = cx + ex * w, y + h * 0.4
        if blink or squint:
            cv.line(ehx - er * 1.2, ehy, ehx + er * 1.2, ehy - (er * 0.6 if squint else 0), CINK, width=er * 0.9)
        else:
            cv.rect(ehx - er, ehy - er * 1.4, 2 * er, 2.8 * er, CINK, radius=er)
            cv.rect(ehx - er * 0.4, ehy - er, er * 0.8, er * 0.8, PAPER, radius=er * 0.4)
    cv.arc(cx, y + h * 0.58, w * 0.14, 0.15 * math.pi, 0.85 * math.pi, CINK, width=7)
    if name:
        cv.mark(name, x, y, w, h)
    return Box(x, y, w, h)


def _bubble(cv, box, tail, copy, f):
    """A speech balloon with its tail pointing at `tail`."""
    ctx = cv.ctx
    cx, cy = box.cx, box.cy
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(box.w / 2, box.h / 2)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    bx = cx + (tail[0] - cx) * 0.25
    ctx.move_to(bx - 24, box.bottom - 18)
    ctx.line_to(*tail)
    ctx.line_to(bx + 20, box.bottom - 14)
    ctx.set_source_rgba(*vb.rgba('#ffffff'))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(CINK))
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(box.w / 2 - 3, box.h / 2 - 3)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*vb.rgba('#ffffff'))
    ctx.fill()
    lines, (w, h) = kit.lines_of(copy, f, box.w * 0.7)
    text.draw(cv, lines, f, cx - box.w * 0.35, cy - h / 2, CINK, align='center', width=box.w * 0.7)
    cv.mark('bubble', *box)


def comic_hq(cv, s, st):
    """Panel one: Lumi at HQ, the plan in hand."""
    panel = _panel(cv, st, '#cfe3ef', (14, 4.2, '#8fb8d4', 0.5, 1.0))
    with cv.clip(*panel):
        # A window of city at dusk behind, flat and dotted.
        floor = panel.y + panel.h * pick(st, 0.78, 0.82)
        cv.rect(panel.x, floor, panel.w, panel.bottom - floor, '#e6c38f')
        for i in range(9):
            bw = panel.w / 9
            bh = panel.h * (0.18 + 0.12 * ((i * 7) % 5) / 4)
            cv.rect(panel.x + i * bw, floor - bh, bw - 6, bh, '#5d84a6')
        cv.line(panel.x, floor, panel.right, floor, CINK, width=6)
    size = pick(st, 230, 250)
    lx = pick(st, panel.x + panel.w * 0.3, panel.cx - 40)
    hop = abs(math.sin(math.pi * min(1, s.f / 14))) * 30 if s.f < 14 else 0
    _lumi(cv, lx, floor - hop, size, blink=10 <= s.f % 40 < 13)
    f = kit.font(pick(st, 34, 34), 850, tracking=0.01, line_height=1.1)
    bw, bh = pick(st, (420, 230), (440, 240))
    bx = pick(st, panel.x + panel.w * 0.56, panel.x + panel.w * 0.12)
    by = pick(st, panel.y + panel.h * 0.2, panel.y + panel.h * 0.22)
    a = kit.prog(s.f, 4, 12, vb.ease_out_back)
    with kit.scaled(cv, bx + bw / 2, by + bh, max(0.01, a)):
        _bubble(cv, Box(bx, by, bw, bh), (lx + size * 0.3, floor - size * 0.95), 'ONE CALM PLAN... FOR EVERYONE!', f)
    _caption(cv, panel, 'MEANWHILE, AT LUMEN HQ...', pick(st, 28, 28))


def comic_close(cv, s, st):
    """Panel two: an extreme close-up, speed lines behind."""
    panel = _panel(cv, st, YELLOW)
    ctx = cv.ctx
    cx, cy = panel.cx + pick(st, 120, 0), panel.cy + pick(st, 40, 140)
    with cv.clip(*panel):
        for i in range(40):   # speed lines, radiating
            a = 2 * math.pi * i / 40 + 0.04 * math.sin(i * 3.1)
            r0, r1 = pick(st, 300, 330), 1400
            ctx.new_path()
            ctx.move_to(cx + r0 * math.cos(a), cy + r0 * math.sin(a))
            ctx.line_to(cx + r1 * math.cos(a - 0.03), cy + r1 * math.sin(a - 0.03))
            ctx.line_to(cx + r1 * math.cos(a + 0.03), cy + r1 * math.sin(a + 0.03))
            ctx.close_path()
            ctx.set_source_rgba(*vb.rgba(CINK if i % 2 else '#ffffff', 0.85))
            ctx.fill()
        push = vb.log_lerp(1.0, 1.08, s.f / s.length)
        size = pick(st, 620, 640) * push
        body = _lumi(cv, cx, cy + size * 0.55, size, name=None)   # cropped by the panel, on purpose
    cv.mark('face', body.cx - body.w * 0.3, body.y + body.h * 0.25, body.w * 0.6, body.h * 0.45)
    f = kit.font(pick(st, 92, 84), 900, tracking=0.02)
    word = 'WHOA!'
    w = text.measure(word, f)
    x, y = pick(st, panel.x + 40, panel.cx - w / 2), panel.y + 30
    pop = min(1.15, kit.spring(s.f, -3, vb.damped(0.4, hz=3)))
    with kit.scaled(cv, x + w / 2, y + 50, max(0.01, pop)):
        text.draw(cv, word, f, x + 6, y + 6, CINK)
        text.draw(cv, word, f, x, y, RED)
    cv.mark('sound', x, y, w, text.line_height(f))


def comic_launch(cv, s, st):
    """Panel three: the launch burst over the Lumen orb."""
    panel = _panel(cv, st, PAPER, (13, 3.4, '#e5b9b0', 0.3, 1.0))
    ctx = cv.ctx
    r = pick(st, 175, 190)
    bx, by = (panel.x + panel.w * 0.3, panel.cy + 40) if st.wide else (panel.cx - 30, panel.y + panel.h * 0.7)
    for radius, colour in ((r, BLUE), (r * 0.62, YELLOW)):
        ctx.save()
        ctx.new_path()
        ctx.arc(bx, by, radius, 0, 2 * math.pi)
        ctx.clip()
        cv.rect(bx - radius, by - radius, 2 * radius, 2 * radius, colour)
        ctx.new_path()
        ctx.rectangle(bx, by - radius, radius, 2 * radius)
        ctx.clip()
        _dots(cv, 13, 4.4, CINK if colour == BLUE else RED, alpha=0.55, dx=3, dy=-3)   # the dot plate, off register
        ctx.restore()
        cv.arc(bx, by, radius - 4, 0, 2 * math.pi, CINK, width=9)
    cv.mark('ball', bx - r, by - r, 2 * r, 2 * r)
    q = s.f / PERIOD
    rot = math.radians(7) * math.sin(2 * math.pi * 3 * q) + math.radians(3) * math.sin(2 * math.pi * 7 * q + 1.3)
    wob = 1 + 0.06 * math.sin(2 * math.pi * 5 * q + 0.4)
    pop = min(1.15, kit.spring(s.f, -3, vb.damped(0.4, hz=3)))
    ro = pick(st, 230, 185)
    sx, sy = (panel.x + panel.w * 0.7, panel.cy - 10) if st.wide else (panel.cx + 60, panel.y + panel.h * 0.27)
    with kit.scaled(cv, sx, sy, max(0.01, wob * pop)):
        ctx.save()
        ctx.translate(sx, sy)
        ctx.rotate(rot)
        pts = [((ro if i % 2 == 0 else ro * 0.58) * math.cos(math.pi * i / 13 - math.pi / 2),
                (ro if i % 2 == 0 else ro * 0.58) * math.sin(math.pi * i / 13 - math.pi / 2)) for i in range(26)]
        _ink_poly(cv, pts, RED)
        ctx.restore()
        bf = kit.font(pick(st, 60, 52), 900, tracking=0.01)
        w = text.measure('LAUNCH!', bf)
        text.draw(cv, 'LAUNCH!', bf, sx - w / 2, sy - text.line_height(bf) / 2, PAPER)
    cv.mark('burst', sx - ro, sy - ro, 2 * ro, 2 * ro)
    _caption(cv, panel, 'TODAY. 9 A.M.', pick(st, 28, 28))


SCENES = {'comic-hq': comic_hq, 'comic-close': comic_close, 'comic-launch': comic_launch}

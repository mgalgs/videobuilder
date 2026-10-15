"""Ending: logo sting. A three-shape mark -- a half-disc, a square and a dot
-- assembles from three directions, each on its own spring (a heavy slide, a
dropped block, a bouncy pop on beat 1). Then the mark steps aside and the
wordmark slides out from behind it, a tagline settles, and a hard-light band
sweeps once across the whole lockup.

Built from `examples/capabilities/springs-with-character.py` (one spring
per piece, each with its own feel) and `hard-light-sweep.py` (the band).
The mark is plain geometry, not any real logo.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _ending_util as u

# Per format: stacked or side by side, mark size, wordmark sizes, tagline size.
LAYOUT = {
    '16x9': dict(stack=False, mark=150, gap=36, sizes=(92, 80, 68, 58, 50), tag=26),
    '9x16': dict(stack=True, mark=280, gap=56, sizes=(84, 72, 64, 56, 48), tag=28),
    '1x1': dict(stack=True, mark=150, gap=28, sizes=(66, 58, 50, 44, 38), tag=22),
}


def _shapes(cv, x, y, m, f, beat, colors, light=0.0):
    """The mark in the box (x, y, m, m) at frame `f`. `light` > 0 draws it
    brightened (the sweep's lit pass) and fully assembled."""
    a_col, b_col, c_col = (kit.mix(c, '#ffffff', light) if light else c for c in colors)
    ctx = cv.ctx
    # A: the half-disc slides in from the left, turning half a turn as it comes.
    pa = 1.0 if light else u.spring(f, 0.75, 1.5)
    if pa > 0.001:
        cx, cy = x + m * 0.5 - (1 - pa) * m * 1.6, y + m * 0.5
        ang = (1 - pa) * math.pi
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(ang)
        ctx.new_path()
        ctx.move_to(0, -m * 0.5)
        ctx.arc_negative(0, 0, m * 0.5, -math.pi / 2, math.pi / 2)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(a_col, vb.clamp01(pa * 3)))
        ctx.fill()
        ctx.restore()
    # B: the square drops from above and lands with a little bounce.
    pb = 1.0 if light else u.spring(f - beat * 0.35, 0.38, 2.4)
    if pb > 0.001:
        side = m * 0.42
        bx, by = x + m * 0.58, y + m * 0.58 - (1 - pb) * m * 1.4
        cv.rect(bx, by, side, side, b_col, radius=m * 0.04, alpha=vb.clamp01(pb * 3))
    # C: the dot pops on beat 1, overshooting.
    pc = 1.0 if light else max(0.0, u.spring(f - beat, 0.3, 3.0))
    if pc > 0.001:
        r = m * 0.18 * pc
        cv.rect(x + m * 0.79 - r, y + m * 0.21 - r, 2 * r, 2 * r, c_col, radius=r)


def _band(ctx, x, y, w, h, skew):
    ctx.new_path()
    ctx.move_to(x, y)
    ctx.line_to(x + w, y)
    ctx.line_to(x + w - skew, y + h)
    ctx.line_to(x - skew, y + h)
    ctx.close_path()


def draw(cv, shot):
    cv.fill(kit.BG)
    data, f = shot.data, shot.f
    name = cv.format.name if cv.format is not None and cv.format.name in LAYOUT else '16x9'
    L = LAYOUT[name]
    pal = list(data['palette']) + [kit.ACCENT, kit.TEAL, kit.INK]
    colors = pal[:3]
    beat = u.fpb(shot)
    W, H = cv.width, cv.height
    s = vb.Box.of(cv).pad(48)
    m, gap = L['mark'], L['gap']

    word = data['name']
    tag = data['tagline']
    footer = data['footer']
    room = s.w if L['stack'] else s.w - m - gap
    word_f, word_lines, ww, wh = u.fit(word, L['sizes'], 820, room, 1, tracking=-0.03)
    tag_f, tag_lines, tw, th = (u.fit(tag, (L['tag'], L['tag'] - 2, L['tag'] - 4), 500, room, 2)
                                if tag else (None, (), 0, 0))
    foot_f = kit.mono(16, 500, tracking=0.14)

    # Final lockup geometry; the mark starts centred and moves to it.
    slide = u.smoother((f - beat * 1.6) / (beat * 0.9))
    if L['stack']:
        block = m + gap + wh + (16 + th if tag else 0)
        top = s.y + (s.h - block) * (0.44 if H > W else 0.36)
        mx1, my1 = s.cx - m / 2, top
        mx0, my0 = mx1, s.cy - m / 2 - (40 if H > W else 0)
        wx, wy = s.cx - ww / 2, top + m + gap
        tx, ty = s.cx - tw / 2, wy + wh + 16
    else:
        total = m + gap + max(ww, tw)
        mx1, my1 = s.cx - total / 2, s.cy - m / 2 - (12 if tag else 0)
        mx0, my0 = s.cx - m / 2, my1
        wx = mx1 + m + gap
        wy = my1 + m / 2 - wh / 2 - (th / 2 + 8 if tag else 0)
        tx, ty = wx, wy + wh + 16
    mx, my = mx0 + (mx1 - mx0) * slide, my0 + (my1 - my0) * slide

    # A soft glow of the first colour behind the mark.
    glow = vb.clamp01(f / (beat * 1.2))
    cv.shadow(mx, my, m, m, radius=m / 2, blur=m * 1.1, spread=m * 0.1, color=(*kit.mix(colors[0], kit.BG, 0.2),
                                                                                  0.22 * glow))
    _shapes(cv, mx, my, m, f, beat, colors)
    cv.mark('mark', mx1, my1, m, m)

    # The wordmark slides out from behind the mark, clipped at the mark's edge.
    if slide > 0:
        p = u.spring(f - beat * 1.8, 0.8, 2.0)
        ctx = cv.ctx
        ctx.save()
        if L['stack']:
            ctx.rectangle(0, max(wy, my + m + 2), W, H)
            dx, dy = 0, -(1 - p) * (wh + gap)
        else:
            ctx.rectangle(max(wx, mx + m + 2), 0, W, H)
            dx, dy = -(1 - p) * (ww + gap), 0
        ctx.clip()
        text.draw(cv, word_lines, word_f, wx + dx, wy + dy, kit.INK)
        ctx.restore()
    cv.mark('wordmark', wx, wy, ww, wh)

    if tag:
        q = u.spring(f - beat * 2.4, 0.9, 2.0)
        with cv.layer(opacity=vb.clamp01(q), dy=(1 - q) * 14):
            text.draw(cv, tag_lines, tag_f, tx, ty, kit.MUTED, align='center' if L['stack'] else 'left', width=tw)
        cv.mark('tagline', tx, ty, tw, th)

    if footer:
        fw, fh = text.block_size([footer], foot_f)
        fy = s.bottom - fh - (60 if H > W else 0)
        a = vb.clamp01((f - beat * 2.8) / 8)
        cv.line(s.cx - 18, fy - 16, s.cx + 18, fy - 16, colors[0], width=2, alpha=a)
        text.draw(cv, [footer], foot_f, s.cx - fw / 2, fy, kit.MUTED, alpha=a)
        cv.mark('footer', s.cx - fw / 2, fy, fw, fh)

    # One hard-light band across the lockup, once it has landed.
    sweep = vb.clamp01((f - beat * 3.1) / (beat * 1.1))
    if 0 < sweep < 1:
        x0 = min(mx1, wx, tx) - 80
        x1 = max(mx1 + m, wx + ww, tx + tw) + 200
        y0, y1 = min(my1, wy) - 10, max(my1 + m, wy + wh) + 10
        bw = 90 if not L['stack'] else 120
        bx = x0 + (x1 - x0) * u.smoother(sweep)
        ctx = cv.ctx
        ctx.save()
        _band(ctx, bx, y0, bw, y1 - y0, (y1 - y0) * 0.35)
        ctx.clip()
        _shapes(cv, mx, my, m, f, beat, colors, light=0.6)
        text.draw(cv, word_lines, word_f, wx, wy, '#fff3dc')
        ctx.restore()


COMPONENT = Component(
    id='logo-sting',
    kind='ending',
    description=('A logo sting: a three-shape mark assembles on springs (a sliding half-disc, a dropped square, a dot '
                 'that pops on beat 1), then the wordmark slides out from behind it and a band of light sweeps across.'),
    tags=('ending', 'logo', 'sting', 'brand', 'wordmark', 'outro', 'spring'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('name', 'text', True, 'The wordmark: a short name, one or two words, e.g. "Northwind".', max_length=14),
        Slot('tagline', 'text', False, 'A short line under the name, e.g. "Films that make themselves".',
             max_length=40),
        Slot('footer', 'text', False, 'A tiny line at the foot of the frame: a web address or a handle.',
             max_length=28),
        Slot('palette', 'palette', False, 'Three colours for the half-disc, the square and the dot, in that order.'),
    ),
    sample={'name': 'Harbor & Kite', 'tagline': 'Small studio, big pictures', 'footer': 'harborkite.example',
           'palette': (kit.ACCENT, kit.TEAL, kit.INK)},
    draw=draw,
)

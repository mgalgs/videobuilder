"""Ending: call to action. A mono kicker types on, a heavy headline rises in
word by word, and a button draws its own outline, fills, and is clicked by a
cursor exactly on beat 2 -- it squashes, springs back and throws a ring of
light. A halftone disc in the corner gives the frame a printed, poster feel.

Built from `examples/capabilities/staggered-reveals.py` (the word stagger),
`pop-on-the-beat.py` (the click) and `comic-halftone.py` (the dot disc).
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _ending_util as u

# Per format: safe pad, headline column width and sizes, max lines, disc radius (of the short side).
LAYOUT = {
    '16x9': dict(pad=56, col=640, sizes=(76, 68, 60, 52), lines=3, disc=0.78, dx=0.08, dy=0.04, kick=20,
                 btn=(30, 28, 26)),
    '9x16': dict(pad=48, col=444, sizes=(76, 68, 60, 52, 46), lines=4, disc=0.86, dx=0.10, dy=-0.12, kick=20,
                 btn=(30, 28, 26, 24, 22)),
    '1x1': dict(pad=48, col=444, sizes=(60, 54, 48, 42), lines=3, disc=0.50, dx=-0.02, dy=-0.10, kick=16,
                btn=(26, 24, 22, 20)),
}
CURSOR = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def _ink_on(color):
    """Dark or light text, whichever reads on `color`."""
    r, g, b, _ = vb.rgba(color)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return kit.BG if lum > 0.38 else kit.INK


def _pill_path(ctx, x, y, w, h):
    r = h / 2
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, math.pi / 2)
    ctx.arc(x + r, y + r, r, math.pi / 2, 3 * math.pi / 2)
    ctx.close_path()


def _pill_outline_pts(x, y, w, h, n=96):
    """The pill's perimeter as points, starting at the left end, for a drawn-on stroke."""
    r = h / 2
    pts = []
    for i in range(n // 2 + 1):
        a = math.pi / 2 + math.pi * i / (n // 2)
        pts.append((x + r + r * math.cos(a), y + r + r * math.sin(a)))
    for i in range(n // 2 + 1):
        a = -math.pi / 2 + math.pi * i / (n // 2)
        pts.append((x + w - r + r * math.cos(a), y + r + r * math.sin(a)))
    return pts


def draw(cv, shot):
    from videobuilder import paths
    cv.fill(kit.BG)
    data, f = shot.data, shot.f
    L = LAYOUT[cv.format.name] if cv.format is not None and cv.format.name in LAYOUT else LAYOUT['16x9']
    accent = data['accent']
    beat = u.fpb(shot)
    click = 2 * beat
    s = vb.Box.of(cv).pad(L['pad'])
    W, H = cv.width, cv.height
    short = min(W, H)

    # Layout first, so the block can be centred as a whole.
    kick_f = kit.mono(L['kick'], 600, tracking=0.12)
    kicker = data['kicker'].upper()
    kick_h = text.line_height(kick_f) if kicker else 0
    head_f, head_lines, head_w, head_h = u.fit(data['headline'], L['sizes'], 850, L['col'], L['lines'],
                                              tracking=-0.025)
    btn_f, btn_lines, btn_tw, btn_th = u.fit(data['action'], L['btn'], 600, s.w - 120, 1, family=kit.MONO)
    pad_x, pad_y, arrow = 28, 16, 34
    bw, bh = btn_tw + 2 * pad_x + arrow, btn_th + 2 * pad_y
    gap1, gap2 = (18 if kicker else 0), 40
    block = kick_h + gap1 + head_h + gap2 + bh
    top = s.y + (s.h - block) * (0.42 if H > W else 0.5)

    # The halftone disc, off the bottom-right corner, swelling in and kicked by the click.
    disc_r = short * L['disc']
    dcx, dcy = W - short * L['dx'], H - short * L['dy']
    grow = u.spring(f, 0.7, 1.6)
    kick = 1 + 0.05 * math.exp(-max(0, f - click) / 6) * (f >= click)
    r = disc_r * grow * kick
    if r > 1:
        ctx = cv.ctx
        ctx.save()
        ctx.new_path()
        ctx.arc(dcx, dcy, r, 0, 2 * math.pi)
        ctx.clip()
        cv.fill(accent, alpha=0.10)
        ctx.set_source(vb.halftone_pattern(14, 3.4, angle=math.radians(20), color=accent))
        ctx.paint_with_alpha(0.55)
        ctx.restore()
        for k, rr in enumerate((1.0, 1.16, 1.32)):
            cv.arc(dcx, dcy, r * rr, 0, 2 * math.pi, accent, width=2, alpha=0.35 - 0.1 * k)

    y = top
    # Kicker: types on, a character every frame, with a block caret.
    if kicker:
        shown = int(vb.clamp01((f - 2) / max(1, len(kicker))) * len(kicker))
        if shown:
            text.draw(cv, [kicker[:shown]], kick_f, s.x, y, accent)
        kw = text.measure(kicker, kick_f)
        if shown < len(kicker) or (f // 8) % 2 == 0 and f < click:
            cx = s.x + text.measure(kicker[:shown], kick_f) + 4
            cv.rect(cx, y + 3, kick_f.size * 0.55, kick_h - 6, accent, alpha=0.8)
        cv.mark('kicker', s.x, y, kw, kick_h)
        y += kick_h + gap1

    # Headline: each line is a mask; its words rise into it one after another.
    lh = text.line_height(head_f)
    space = text.measure(' ', head_f)
    k = 0
    for i, line in enumerate(head_lines):
        ly = y + i * lh
        x = s.x
        with cv.clip(s.x - 20, ly - 4, W, lh + 8):
            for word in line.split(' '):
                p = u.spring(f - 5 - 3 * k, 0.62, 2.2)
                text.draw(cv, [word], head_f, x, ly + (1 - p) * lh * 1.05, kit.INK)
                x += text.measure(word, head_f) + space
                k += 1
    cv.mark('headline', s.x, y, head_w, head_h)
    y += head_h + gap2

    # The button: outline draws on, the fill wipes in behind it, then the click.
    bx, by = s.x, y
    t_line = vb.clamp01((f - beat * 0.8) / (beat * 0.7))
    t_fill = u.smoother((f - beat * 1.2) / (beat * 0.5))
    press = 0.0
    if f >= click:
        d = f - click
        press = 1 - vb.spring_at(d, 30, **vb.damped(0.32, hz=3.2))  # 1 on the beat, overshoots, settles to 0
    sc = 1 - 0.08 * press
    ocx, ocy = bx + bw / 2, by + bh / 2
    with cv.layer(dx=ocx * (1 - sc), dy=ocy * (1 - sc), scale=sc):
        ctx = cv.ctx
        if t_fill > 0:
            ctx.save()
            ctx.rectangle(bx - 2, by - 2, (bw + 4) * t_fill, bh + 4)
            ctx.clip()
            _pill_path(ctx, bx, by, bw, bh)
            ctx.set_source_rgba(*vb.rgba(accent))
            ctx.fill()
            ctx.restore()
        if 0 < t_line:
            pts = paths.reveal(_pill_outline_pts(bx, by, bw, bh), u.smoother(t_line), closed=True)
            if len(pts) > 1:
                paths.draw(cv, pts, accent, width=3)
        if t_fill > 0:
            label = _ink_on(accent)
            with cv.layer(opacity=vb.clamp01((f - beat * 1.5) / 6)):
                text.draw(cv, btn_lines, btn_f, bx + pad_x, by + pad_y, label)
                ax, ay = bx + bw - pad_x - 18, by + bh / 2
                cv.line(ax - 4, ay, ax + 16, ay, label, width=3)
                u.fill_poly(cv, [(ax + 20, ay), (ax + 10, ay - 8), (ax + 10, ay + 8)], label)
    cv.mark('button', bx, by, bw, bh)

    # The click's ring burst, and the cursor that makes it.
    if f >= click:
        d = f - click
        for j in range(2):
            age = d - 3 * j
            if 0 <= age < 20:
                g = 1 - (1 - age / 20) ** 3
                grow_px = 6 + 34 * g
                cv.outline(bx - grow_px, by - grow_px, bw + 2 * grow_px, bh + 2 * grow_px, accent,
                           width=3 - j, radius=bh / 2 + grow_px, alpha=0.7 * (1 - age / 20))
    tx, ty = bx + bw - pad_x - arrow - 4, by + bh * 0.62
    arrive = vb.interpolate(f, [beat, click - 2], [0, 1], ease=vb.ease_out_expo)
    leave = vb.interpolate(f, [click + 10, click + 26], [0, 1], ease=vb.ease_in_out_quart)
    if 0 < arrive and leave < 1:
        sx0, sy0 = W + 30, H + 40
        cx = sx0 + (tx - sx0) * arrive + 60 * leave
        cy = sy0 + (ty - sy0) * arrive + 40 * leave
        cs = (1 - 0.15 * press) * (1.25 if H > W else 1.1)
        pts = [(cx + px * cs, cy + py * cs) for px, py in CURSOR]
        with cv.layer(opacity=1 - leave):
            cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
            u.poly(cv.ctx, pts)
            cv.ctx.set_source_rgba(*vb.rgba(kit.INK))
            cv.ctx.fill_preserve()
            cv.ctx.set_source_rgba(*vb.rgba(kit.BG))
            cv.ctx.set_line_width(2)
            cv.ctx.stroke()


COMPONENT = Component(
    id='cta-pill',
    kind='ending',
    description=('A call to action: a typed kicker, a heavy headline rising word by word, and a drawn button '
                 'a cursor clicks on beat 2 -- it squashes, springs back and throws a ring -- over a halftone disc.'),
    tags=('ending', 'call to action', 'cta', 'button', 'url', 'outro', 'beat'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 8),
    slots=(
        Slot('headline', 'text', True, 'The one bold line asking the viewer to act, e.g. "Start your first film '
             'tonight".', max_length=44),
        Slot('action', 'text', True, 'Short text on the button: a web address or a verb, e.g. "studio.example/start" '
             'or "Join the beta".', max_length=24),
        Slot('kicker', 'text', False, 'A tiny line above the headline, shown in capitals, e.g. "One more thing".',
             max_length=28),
        Slot('accent', 'color', False, 'Colour of the button, the halftone disc and the kicker.'),
    ),
    sample={'headline': 'Start your first film tonight', 'action': 'studio.example/start',
           'kicker': 'Your turn', 'accent': kit.ACCENT},
    draw=draw,
)

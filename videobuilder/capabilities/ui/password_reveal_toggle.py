"""Password reveal toggle: the eye icon at the end of a password field opens
its lid, and the masked dots turn into the characters they were hiding."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _almond(ctx, cx, cy, half, lift, sag):
    """The eye outline: two quadratic lids between the corners, the upper one's
    control `lift` above the centre line, the lower one's `sag` below."""
    x0, x1 = cx - half, cx + half
    ctx.new_path()
    ctx.move_to(x0, cy)
    # quadratic -> cubic: control points two thirds of the way to the quad control
    ctx.curve_to(x0 + 2 / 3 * half, cy - 2 / 3 * lift, x1 - 2 / 3 * half, cy - 2 / 3 * lift, x1, cy)
    ctx.curve_to(x1 - 2 / 3 * half, cy + 2 / 3 * sag, x0 + 2 / 3 * half, cy + 2 / 3 * sag, x0, cy)
    ctx.close_path()


def draw_eye(cv, cx, cy, size, open_, color, width=None, alpha=1.0):
    """An eye icon `size` px wide centred at (cx, cy), its lid `open_` from 0
    (shut: one curved lid with lashes hanging down) to 1 (open: an almond with
    a round iris). Values between show the lid part-way, so animating
    `open_` blinks the eye open or shut."""
    o = vb.clamp01(open_)
    half, h = size / 2, size * 0.42
    width = width or max(1.5, size * 0.08)
    sag = h
    lift = 2 * h * o - h          # shut: the upper lid lies on the lower one
    ctx = cv.ctx
    rgba = vb.canvas.rgba(color, alpha)
    ctx.save()
    if o > 0.02:
        _almond(ctx, cx, cy, half, lift, sag)
        ctx.clip()
        ctx.new_path()
        ctx.arc(cx, cy + h * 0.08, size * 0.2, 0, 2 * math.pi)
        ctx.set_source_rgba(*rgba)
        ctx.fill()
    ctx.restore()
    ctx.save()
    _almond(ctx, cx, cy, half, lift, sag)
    ctx.set_source_rgba(*rgba)
    ctx.set_line_width(width)
    ctx.set_line_join(1)  # round
    ctx.stroke()
    ctx.restore()
    lash = 1 - vb.clamp01(o * 2.5)
    if lash > 0:                  # lashes along the shut lid, gone as it lifts
        for t in (0.22, 0.5, 0.78):
            # point and normal on the lower lid's quadratic
            px = cx - half + 2 * half * t
            py = cy + 2 * t * (1 - t) * sag
            dy = 2 * (1 - 2 * t) * sag
            nx, ny = -dy, 2 * half
            k = size * 0.16 / math.hypot(nx, ny)
            cv.line(px, py, px + nx * k, py + ny * k, color, width=width,
                    alpha=alpha * lash)
    cv.mark('eye', cx - half, cy - h, size, 2 * h)


def draw_masked(cv, text, font, x, y, p, color, stagger=0.6):
    """`text` from its top-left (x, y), each character shown as a dot while
    masked and as itself once revealed. `p` runs 0 (all dots) to 1 (all
    characters), the swap rolling left to right over `stagger` of the run;
    each dot shrinks away as its character grows in. Run `p` from 1 to 0 to
    hide it again. Returns the Box of the line."""
    w, h = vb.text.block_size([text], font)
    n = max(1, len(text))
    left = x
    r = font.size * 0.14 if hasattr(font, 'size') else h * 0.12
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        s = vb.clamp01((p - stagger * i / n) / (1 - stagger)) if stagger < 1 else vb.clamp01(p)
        s = vb.ease_out_back(s) if 0 < s < 1 else s
        if s < 1:
            demo.dot(cv, left + adv / 2, y + h * 0.55, r * max(0.0, 1 - s), color=color)
        if s > 0:
            cw, chh = vb.text.block_size([ch], font)
            with cv.layer(dx=left + adv / 2, dy=y + h / 2, scale=max(0.01, s)):
                vb.text.draw(cv, [ch], font, -cw / 2, -chh / 2, color, alpha=vb.clamp01(s))
        left += adv
    return vb.Box(x, y, w, h)


def _pointer(cv, x, y, s=1.0, color=demo.INK):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    ctx = cv.ctx
    ctx.new_path()
    for i, (px, py) in enumerate(pts):
        (ctx.move_to if i == 0 else ctx.line_to)(x + px * s, y + py * s)
    ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba(color))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.canvas.rgba(demo.BG))
    ctx.set_line_width(2 * s)
    ctx.stroke()


def draw(n, cv):
    fw, fh = 400, 64
    fx, fy = (demo.W - fw) / 2, (demo.H - fh) / 2
    demo.word(cv, 'Password', fx + 40, fy - 24, size=16, color=demo.MUTED, weight=600)
    cv.rect(fx, fy, fw, fh, '#ffffff', radius=10, alpha=0.06)
    cv.outline(fx, fy, fw, fh, demo.LINE, width=1.5, radius=10)
    ex, ey = fx + fw - 38, fy + fh / 2

    move = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.0))
    press = demo.phase(n, 1.0, 1.08) - demo.phase(n, 1.08, 1.2)
    p = demo.phase(n, 1.05, 1.5)
    reveal = demo.phase(n, 1.1, 1.9)

    if press > 0:
        demo.dot(cv, ex, ey, 24, color=demo.ACCENT, alpha=0.18 * press)
    draw_eye(cv, ex, ey, 34, vb.ease_out_quint(p), demo.ACCENT)
    f = demo.mono(28, 600)
    box = draw_masked(cv, 'sunset42', f, fx + 24, fy + (fh - vb.text.block_size(['s'], f)[1]) / 2,
                      reveal, demo.INK)
    cv.mark('text', *box)

    sx, sy = demo.W * 0.72, demo.H * 0.78
    cx, cy = sx + (ex + 3 - sx) * move, sy + (ey + 2 - sy) * move
    away = vb.ease_in_out_quart(demo.phase(n, 1.5, 2.1))   # step aside so the open eye shows
    cx, cy = cx + 34 * away, cy + 30 * away
    _pointer(cv, cx, cy, s=0.7 * (1 - 0.12 * press))


CAPABILITY = Capability(
    id='password-reveal-toggle',
    name='Password reveal toggle',
    family='ui',
    group='Forms',
    aliases=('eye toggle', 'show password icon', 'show/hide password'),
    definition='Clicking the eye at the end of a password field lifts its lid open, '
               'and the row of masking dots turns into the typed characters.',
    phrasings=('the little eye opens and the password dots become real letters',
               'click show password and the hidden text appears',
               'an eye icon that blinks open to unmask the password'),
    related=('plus-to-close-rotate', 'image-hover-mask-reveal', 'blinking-cursor', 'toggle-switch-slide',
             'fade-up-scroll-reveal', 'circular-clip-reveal'),
    api=('videobuilder.capabilities.ui.password_reveal_toggle.draw_eye',
         'videobuilder.capabilities.ui.password_reveal_toggle.draw_masked'),
    demo=lambda: demo.film(draw),
)

"""Images: before/after wipe. Two pictures of the same thing, one over the
other. The "before" holds for a beat; then a glowing divider sweeps almost
all the way across to show the "after", springs back past the middle and
settles there, so both halves sit side by side, its round handle pulsing on
each beat. Labels sit in each half's corner, and the one the divider covers
is covered with its half.

Laid out per format: the divider runs top to bottom and sweeps sideways in
16:9 and 1:1; in 9:16 it runs across and sweeps upward, so each half keeps
the full width of the tall frame.
"""
import math

import videobuilder as vb
from videobuilder import Box, text

from .. import kit
from ..schema import Component, Slot
from . import _images_util as u

SETTLE = vb.damped(0.42, hz=1.5)
FAR = 0.12   # how far the first sweep goes, as a fraction of the frame
REST = 0.5
HANDLE_R = 24


def _pos(shot):
    """Divider position, 0-1 along the sweep axis: 1 shows only the before."""
    fpb = u.beat_frames(shot)
    f = shot.f
    if f < fpb:
        return 1.0
    sweep = max(10.0, fpb)
    if f < fpb + sweep:
        return 1 - (1 - FAR) * vb.ease_in_out_quart((f - fpb) / sweep)
    return FAR + (REST - FAR) * vb.spring_at(f - fpb - sweep, 30, **SETTLE)


def _chip(cv, label, x, y, dot, align_right=False, W=None):
    f = kit.mono(15, 700, tracking=0.16)
    t = label.upper()
    tw = text.measure(t, f)
    ch = text.line_height(f) + 16
    cw = tw + 16 + 26
    if align_right:
        x = x - cw
    cv.rect(x, y, cw, ch, kit.BG, radius=ch / 2, alpha=0.82)
    cv.ctx.arc(x + 16, y + ch / 2, 5, 0, 2 * math.pi)
    u.fill(cv.ctx, dot)
    text.draw(cv, [t], f, x + 28, y + 8, kit.INK)
    return Box(x, y, cw, ch)


def draw(cv, shot):
    data = shot.data
    W, H = cv.width, cv.height
    frame = Box.of(cv)
    accent = data['accent']
    across = H > W * 1.2   # 9:16: a horizontal divider, sweeping upward
    t = vb.clamp01(shot.f / max(1, shot.length - 1))
    zoom = 1.02 + 0.06 * t
    fx = 0.48
    pos = _pos(shot)
    u.cover_image(cv, data['before'], frame, zoom=zoom, fx=fx)
    if across:
        split = H * pos
        after_r = Box(0, split, W, H - split)
        before_r = Box(0, 0, W, split)
    else:
        split = W * pos
        after_r = Box(split, 0, W - split, H)
        before_r = Box(0, 0, split, H)
    if after_r.w > 0 and after_r.h > 0:
        with cv.clip(*after_r):
            u.cover_image(cv, data['after'], frame, zoom=zoom, fx=fx)
            # a hard-light band on the after side, just past the divider
            ctx = cv.ctx
            if across:
                g = u.linear(ctx, 0, split, 0, split + 90, [(0, (255, 244, 220, 0.35)), (1, (255, 244, 220, 0))])
            else:
                g = u.linear(ctx, split, 0, split + 90, 0, [(0, (255, 244, 220, 0.35)), (1, (255, 244, 220, 0))])
            ctx.rectangle(*frame)
            u.fill(ctx, g)
    u.vignette(cv, frame, 0.35)
    cv.mark('photo', *frame)

    # labels, each in its own half's corner, covered with its half
    m = 32
    before_label, after_label = data['before_label'], data['after_label']
    if before_label:
        with cv.clip(*before_r):
            box = _chip(cv, before_label, m, m, kit.MUTED)
        if before_r.contains(box, tolerance=0):
            cv.mark('before-label', *box)
    if after_label:
        if across:
            x, y, right = m, H * REST + m, False
        else:
            x, y, right = W - m, m, True
        with cv.clip(*after_r):
            box = _chip(cv, after_label, x, y, accent, align_right=right)
        if after_r.contains(box, tolerance=0):
            cv.mark('after-label', *box)

    # the divider: a line with a glow, and a round handle
    ctx = cv.ctx
    if pos < 1:
        if across:
            ctx.rectangle(0, split - 14, W, 28)
            u.fill(ctx, u.linear(ctx, 0, split - 14, 0, split + 14,
                                 [(0, (255, 255, 255, 0)), (0.5, (255, 255, 255, 0.35)), (1, (255, 255, 255, 0))]))
            cv.rect(0, split - 1.5, W, 3, kit.INK)
            hx, hy = W / 2, split
        else:
            ctx.rectangle(split - 14, 0, 28, H)
            u.fill(ctx, u.linear(ctx, split - 14, 0, split + 14, 0,
                                 [(0, (255, 255, 255, 0)), (0.5, (255, 255, 255, 0.35)), (1, (255, 255, 255, 0))]))
            cv.rect(split - 1.5, 0, 3, H, kit.INK)
            hx, hy = split, H / 2
        fpb = u.beat_frames(shot)
        beat_age = shot.f % fpb
        if shot.f >= 2 * fpb and beat_age < 14:
            e = beat_age / 14
            ctx.arc(hx, hy, HANDLE_R + 4 + 22 * e, 0, 2 * math.pi)
            ctx.set_source_rgba(*vb.rgba(accent, 0.7 * (1 - e)))
            ctx.set_line_width(3)
            ctx.stroke()
        cv.shadow(hx - HANDLE_R, hy - HANDLE_R, 2 * HANDLE_R, 2 * HANDLE_R, radius=HANDLE_R, dy=4, blur=12,
                  color=(0, 0, 0, 0.45))
        ctx.arc(hx, hy, HANDLE_R, 0, 2 * math.pi)
        u.fill(ctx, kit.INK)
        ctx.arc(hx, hy, HANDLE_R, 0, 2 * math.pi)
        ctx.set_source_rgba(*vb.rgba(accent))
        ctx.set_line_width(3)
        ctx.stroke()
        ctx.save()
        ctx.translate(hx, hy)
        if across:
            ctx.rotate(math.pi / 2)
        for s in (-1, 1):
            u.poly(ctx, [(s * 5, -7), (s * 13, 0), (s * 5, 7)])
            u.fill(ctx, kit.BG)
        ctx.restore()
        cv.mark('handle', hx - HANDLE_R, hy - HANDLE_R, 2 * HANDLE_R, 2 * HANDLE_R)

    caption = data['caption']
    if caption:
        k = shot.f - 4
        q = vb.ease_out_quint(vb.clamp01(k / 14))
        if q > 0:
            f, lines = u.fit_lines(caption, min(W - 2 * 40, 560) - 40, (30, 27, 24, 22), weight=750, max_lines=2)
            tw, th = text.block_size(lines, f)
            cw, ch = tw + 40, th + 26
            cx = (W - cw) / 2
            cy = H - (H * 0.1 if across else 32) - ch + (1 - q) * 30
            cv.rect(cx, cy, cw, ch, kit.BG, radius=14, alpha=0.85 * q)
            text.draw(cv, lines, f, cx + 20, cy + 13, kit.INK, align='center', width=tw, alpha=q)
            cv.mark('caption', cx, cy, cw, ch)


COMPONENT = Component(
    id='before-after-wipe',
    kind='images',
    description='Two pictures of the same thing: a glowing divider sweeps across to reveal the after, springs '
                'back to the middle and holds both side by side, with a label in each half and a caption.',
    tags=('images', 'comparison', 'before-after', 'wipe', 'reveal', 'transformation'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('before', 'image', True, 'The "before" picture.'),
        Slot('after', 'image', True, 'The "after" picture, ideally the same framing as the before.'),
        Slot('before_label', 'text', False, 'Short label on the before half, like "Before" or a date.', max_length=14),
        Slot('after_label', 'text', False, 'Short label on the after half, like "After" or a date.', max_length=14),
        Slot('caption', 'text', False, 'One line about the change, shown at the bottom.', max_length=48),
        Slot('accent', 'color', False, 'Colour of the handle ring, its beat pulse and the after label\'s dot.'),
    ),
    sample={'before': u.photo('before'), 'after': u.photo('after'), 'before_label': 'March',
            'after_label': 'June', 'caption': 'Same valley, twelve weeks apart', 'accent': kit.ACCENT},
    draw=draw,
    overlap_ok=(('photo', 'before-label'), ('photo', 'after-label'), ('photo', 'handle'), ('photo', 'caption')),
)

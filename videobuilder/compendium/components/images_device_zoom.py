"""Images: device zoom. A screenshot inside a drawn device -- a phone for a
tall screenshot, a browser window for a wide one, no brand on either --
rises in on a spring beside a title; then, on a beat, the camera pushes in
onto one area of the screen, the rest of the frame dims to a spotlight
around it, an accent ring lands on it (pulsing on each beat after) and a
callout chip springs up beside it.

The area is given as fractions of the screenshot, so a builder points at it
without knowing any pixel sizes; the push zooms just enough to frame it,
in a spot that leaves room for the callout in every format.
"""
import math

import cairo

import videobuilder as vb
from videobuilder import Box, text

from .. import kit
from ..schema import Component, Slot
from . import _images_util as u

RISE = vb.damped(0.6, hz=1.8)
POP = vb.damped(0.5, hz=2.6)
BODY = '#0e0f13'
RIM = '#3a3d47'
CHROME = '#e4e6eb'


def _device(img):
    """The device drawn at a nominal size: (kind, body w, body h, screen Box in body coords)."""
    if img.h >= img.w:
        sw = 300.0
        sh = sw * min(2.17, max(1.6, img.h / img.w))
        b = 12.0
        return 'phone', sw + 2 * b, sh + 2 * b, Box(b, b, sw, sh)
    sw = 560.0
    sh = sw / min(1.9, max(1.25, img.w / img.h))
    bar = 38.0
    return 'browser', sw, sh + bar, Box(0, bar, sw, sh)


def _layout(W, H, kind, has_title):
    """(device region, title region or None, focus target region) per format."""
    if W > H * 1.2:
        target = Box(W * 0.42, H * 0.1, W * 0.54, H * 0.8)
        if kind == 'phone':
            return Box(W * 0.5, 28, W * 0.46, H - 56), Box(56, 0, W * 0.42, H) if has_title else None, target
        return (Box(W * 0.06, H * 0.3, W * 0.88, H * 0.66), Box(56, 30, W - 112, H * 0.22) if has_title else None,
                target)
    if H > W * 1.2:
        dev = Box(44, 250, W - 88, H - 250 - 56) if has_title else Box(44, 56, W - 88, H - 112)
        if kind == 'browser':  # a wide window, too small to read if it fits: let it run off the right edge
            dev = Box(40, dev.y + 30, W * 1.45, dev.h - 60)
        return dev, Box(40, 70, W - 80, 160) if has_title else None, Box(W * 0.05, H * 0.12, W * 0.9, H * 0.44)
    target = Box(W * 0.06, H * 0.08, W * 0.88, H * 0.56)
    if kind == 'phone':
        return Box(W * 0.5, 24, W * 0.46, H - 48), Box(40, 0, W * 0.44, H) if has_title else None, target
    return Box(30, H * 0.36, W - 60, H * 0.6), Box(40, 36, W - 80, H * 0.28) if has_title else None, target


def _draw_device(cv, img, kind, bw, bh, screen):
    ctx = cv.ctx
    if kind == 'phone':
        cv.shadow(0, 0, bw, bh, radius=44, dy=24, blur=50, color=(0, 0, 0, 0.6))
        cv.rect(-2.5, 70, 3, 40, RIM, radius=1.5)
        cv.rect(-2.5, 124, 3, 64, RIM, radius=1.5)
        cv.rect(bw - 0.5, 110, 3, 70, RIM, radius=1.5)
        cv.rect(0, 0, bw, bh, BODY, radius=46)
        cv.outline(1, 1, bw - 2, bh - 2, RIM, width=2, radius=45)
        u.cover_image(cv, img, screen, fy=0.0, radius=36)
        ctx.arc(bw / 2, screen.y + 16, 6, 0, 2 * math.pi)
        u.fill(ctx, BODY)
    else:
        cv.shadow(0, 0, bw, bh, radius=12, dy=24, blur=50, color=(0, 0, 0, 0.6))
        cv.rect(0, 0, bw, bh, CHROME, radius=12)
        for i in range(3):
            ctx.arc(20 + i * 18, screen.y / 2, 5.5, 0, 2 * math.pi)
            u.fill(ctx, '#c3c6cd')
        pill = Box(bw * 0.28, screen.y / 2 - 11, bw * 0.44, 22)
        cv.rect(*pill, '#ffffff', radius=11)
        cv.rect(pill.x + 10, pill.cy - 4, 7, 8, '#9aa0aa', radius=2)
        text.draw(cv, ['example.com'], kit.font(12, 500), pill.x + 24, pill.cy - 8, '#7b818d')
        with cv.clip(0, 0, bw, bh, 12):
            u.cover_image(cv, img, screen, fy=0.0)
        cv.outline(0.5, 0.5, bw - 1, bh - 1, '#b9bdc6', width=1, radius=12)


def _intersect(a, b):
    x0, y0 = max(a.x, b.x), max(a.y, b.y)
    x1, y1 = min(a.right, b.right), min(a.bottom, b.bottom)
    return Box(x0, y0, max(0, x1 - x0), max(0, y1 - y0))


def _area(data):
    f = data['focus']
    if not f:
        return 0.25, 0.25, 0.5, 0.5
    x, y, w, h = (vb.clamp01(v) for v in f)
    w, h = max(0.05, min(w, 1 - x)), max(0.05, min(h, 1 - y))
    return x, y, w, h


def draw(cv, shot):
    data = shot.data
    img = data['screenshot']
    accent = data['accent']
    W, H = cv.width, cv.height
    frame = Box.of(cv)
    ctx = cv.ctx
    fpb = u.beat_frames(shot)

    # backdrop: a soft accent glow and a fading dot screen, fixed to the frame
    cv.fill(kit.BG)
    ctx.rectangle(0, 0, W, H)
    u.fill(ctx, u.radial(ctx, W * 0.68, H * 0.5, max(W, H) * 0.7, [(0, _tint(accent, 0.28)), (1, _tint(accent, 0.0))]))
    ctx.save()
    ctx.rectangle(0, 0, W, H)
    ctx.set_source(vb.halftone_pattern(14, 1.6, angle=math.radians(20), color=(255, 255, 255, 0.07)))
    ctx.fill()
    ctx.restore()

    kind, bw, bh, screen = _device(img)
    dev_r, title_r, target_r = _layout(W, H, kind, bool(data['title']))
    s0 = min(dev_r.w / bw, dev_r.h / bh)
    # world = the device's own coordinates; at rest it's drawn s0 times, centred in dev_r
    def wide(px, py):
        return dev_r.cx + (px - bw / 2) * s0, dev_r.cy + (py - bh / 2) * s0

    ax, ay, aw, ah = _area(data)
    area = Box(screen.x + ax * screen.w, screen.y + ay * screen.h, aw * screen.w, ah * screen.h)
    zoom = max(1.2, min(4.0, min(target_r.w / (area.w * s0), target_r.h / (area.h * s0))))

    push_at = max(fpb, math.floor(0.3 * shot.length / fpb) * fpb)
    push_len = max(12.0, 1.25 * fpb)
    q = vb.ease_in_out_quart(vb.clamp01((shot.f - push_at) / push_len))
    Z = vb.log_lerp(1.0, zoom, q)
    wcx, wcy = wide(area.cx, area.cy)
    # where the area's centre sits on screen, and the zoom about it
    sx = wcx + (target_r.cx - wcx) * q
    sy = wcy + (target_r.cy - wcy) * q

    def to_screen(px, py):
        x, y = wide(px, py)
        return sx + (x - wcx) * Z, sy + (y - wcy) * Z

    rise = vb.spring_at(shot.f + 4, 30, **RISE)
    lift = 1 - rise
    ctx.save()
    ctx.translate(sx, sy)
    ctx.scale(Z, Z)
    ctx.translate(-wcx, -wcy)
    ctx.translate(dev_r.cx, dev_r.cy + lift * H * 0.6)
    ctx.rotate(math.radians(-7) * lift)
    ctx.scale(s0, s0)
    ctx.translate(-bw / 2, -bh / 2)
    _draw_device(cv, img, kind, bw, bh, screen)
    ctx.restore()
    x0, y0 = to_screen(screen.x, screen.y)
    x1, y1 = to_screen(screen.right, screen.bottom)
    seen = _intersect(Box(x0, y0 + lift * H * 0.6 * Z, x1 - x0, y1 - y0), frame)
    if seen.w > 0 and seen.h > 0:
        cv.mark('device', *seen)

    # the title, beside the device in the wide shot; gone as the push starts
    if title_r is not None:
        fade = 1 - vb.clamp01((shot.f - push_at) / 4)
        if fade > 0:
            sizes = (48, 44, 40, 36, 32, 28) if title_r.w < title_r.h else (44, 40, 36, 32, 28)
            f, lines = u.fit_lines(data['title'], title_r.w, sizes, weight=850, max_lines=4)
            tw, th = text.block_size(lines, f)
            ty = title_r.cy - th / 2
            lh = text.line_height(f)
            for i, ln in enumerate(lines):
                p = vb.ease_out_quint(vb.clamp01((shot.f - 4 - i * 3) / 14))
                text.draw(cv, [ln], f, title_r.x - (1 - p) * 30, ty + i * lh, kit.INK, alpha=p * fade)
            cv.rect(title_r.x, ty - 22, 44 * vb.ease_out_expo(vb.clamp01((shot.f - 2) / 10)), 5, accent, alpha=fade)
            cv.mark('title', title_r.x, ty - 22, tw, th + 22)

    # the spotlight, the ring and the callout, once the push has landed
    k = shot.f - (push_at + push_len)
    if k < 0:
        return
    rx0, ry0 = to_screen(area.x, area.y)
    rx1, ry1 = to_screen(area.right, area.bottom)
    pad = 8
    ring = Box(rx0 - pad, ry0 - pad, rx1 - rx0 + 2 * pad, ry1 - ry0 + 2 * pad)
    dim = vb.clamp01(k / 8)
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.new_path()
    ctx.rectangle(0, 0, W, H)
    ctx.rectangle(*ring)
    u.fill(ctx, (8, 9, 12, 0.62 * dim))
    ctx.restore()
    s = vb.spring_at(k, 30, **POP)
    grow = 1 + 0.12 * (1 - s)
    rr = ring.scaled(grow)
    cv.outline(*rr, accent, width=4, radius=8, alpha=vb.clamp01(s * 1.5))
    for b in range(1, 6):
        age = k - b * fpb + (push_at + push_len) % fpb
        if 0 <= age < 14:
            e = age / 14
            cv.outline(*ring.scaled(1 + 0.18 * e), accent, width=3, radius=8 + 8 * e, alpha=0.6 * (1 - e))
    cv.mark('focus', *ring)

    if data['callout']:
        _callout(cv, data['callout'], ring, frame, accent, k)


def _tint(color, a):
    r, g, b, _ = vb.rgba(color)
    return (r * 255, g * 255, b * 255, a)


def _callout(cv, copy, ring, frame, accent, k):
    W, H = frame.w, frame.h
    f = kit.font(26 if W > H * 1.2 else 24, 700)
    pad_x, pad_y = 20, 14
    if W > H * 1.2:   # to the left of the ring
        maxw = ring.x - 48 - 40
        lines = text.wrap(copy, f, maxw - 2 * pad_x - 22, balance=True)
        tw, th = text.block_size(lines, f)
        cw, ch = tw + 2 * pad_x + 22, th + 2 * pad_y
        cx = max(40, ring.x - 48 - cw)
        cy = min(H - 40 - ch, max(40, ring.cy - ch / 2))
        anchor_chip, anchor_ring = (cx + cw, cy + ch / 2), (ring.x, cy + ch / 2)
    else:             # below the ring
        maxw = W - 72
        lines = text.wrap(copy, f, maxw - 2 * pad_x - 22, balance=True)
        tw, th = text.block_size(lines, f)
        cw, ch = tw + 2 * pad_x + 22, th + 2 * pad_y
        cx = max(36, min(W - 36 - cw, ring.cx - cw / 2))
        cy = min(H - 40 - ch, ring.bottom + 44)
        anchor_chip, anchor_ring = (cx + cw / 2, cy), (cx + cw / 2, ring.bottom)
    s = vb.spring_at(k - 6, 30, **POP)
    if s <= 0.001:
        return
    line_p = vb.clamp01((k - 4) / 6)
    (ax, ay), (bx, by) = anchor_ring, anchor_chip
    cv.line(ax, ay, ax + (bx - ax) * line_p, ay + (by - ay) * line_p, accent, width=2)
    ccx, ccy = cx + cw / 2, cy + ch / 2
    with cv.layer(opacity=vb.clamp01(s * 2), dx=ccx * (1 - s), dy=ccy * (1 - s), scale=s):
        cv.shadow(cx, cy, cw, ch, radius=ch / 2 if len(lines) == 1 else 16, dy=8, blur=20, color=(0, 0, 0, 0.5))
        cv.rect(cx, cy, cw, ch, '#1c1e25', radius=ch / 2 if len(lines) == 1 else 16)
        cv.ctx.arc(cx + pad_x + 5, cy + ch / 2, 5, 0, 2 * math.pi)
        u.fill(cv.ctx, accent)
        text.draw(cv, lines, f, cx + pad_x + 22, cy + pad_y, kit.INK)
    cv.mark('callout', cx, cy, cw, ch)


COMPONENT = Component(
    id='device-zoom',
    kind='images',
    description='A screenshot in a drawn phone (tall image) or browser window (wide image) rises in beside a '
                'title, then the camera pushes in onto one area under a spotlight ring with a callout chip.',
    tags=('images', 'screenshot', 'product', 'app', 'device', 'zoom', 'callout', 'ui'),
    formats=('16x9', '9x16', '1x1'),
    beats=(5, 10),
    slots=(
        Slot('screenshot', 'image', True, 'A screenshot: tall for a phone, wide for a browser window.'),
        Slot('focus', 'series', False, 'The area to zoom onto, as four numbers from 0 to 1: left, top, width, '
             'height, as fractions of the screenshot (default: the middle).', min_count=4, max_count=4),
        Slot('title', 'text', False, 'A headline beside the device before the camera pushes in.', max_length=36),
        Slot('callout', 'text', False, 'A short note on the zoomed-in area.', max_length=44),
        Slot('accent', 'color', False, 'Colour of the ring, the callout dot and the glow behind the device.'),
    ),
    sample={'screenshot': u.app_screen(), 'focus': (0.03, 0.5, 0.94, 0.125),
            'title': 'Every trip, planned in one place', 'callout': 'Budget, packing and drive time at a glance',
            'accent': kit.ACCENT},
    draw=draw,
    overlap_ok=(('device', 'focus'), ('device', 'callout')),
)

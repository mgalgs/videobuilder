"""Shared helpers for the `images` components: a set of procedural sample
pictures (each a different scene, palette and composition, so a preview with
several images never shows the same picture twice), a sample app screenshot,
and a few drawing moves the image components share.

Every picture is drawn here with cairo and kept as a `vb.Image`, so no binary
asset ships with the package. Each is built once, on first use.
"""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage

import videobuilder as vb
from videobuilder import Box, text

from .. import kit

PW, PH = 1200, 800  # sample "photo" size: 3:2, like a camera frame


# ---- small drawing helpers ----

def beat_frames(shot):
    """Frames a beat, at whatever tempo the film this shot sits in runs."""
    beats = shot.segment.until - shot.segment.at
    return shot.length / beats if beats > 0 else 15.0


def to_image(cv):
    """A finished `vb.Canvas` -> an opaque `vb.Image`."""
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    pil = PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA',
                              cv.surface.get_stride(), 1)
    return vb.Image.from_pil(pil.convert('RGB'))


def linear(ctx, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for t, c in stops:
        g.add_color_stop_rgba(t, *vb.rgba(c))
    return g


def radial(ctx, cx, cy, r, stops):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    for t, c in stops:
        g.add_color_stop_rgba(t, *vb.rgba(c))
    return g


def poly(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def fill(ctx, source):
    if isinstance(source, cairo.Pattern):
        ctx.set_source(source)
    else:
        ctx.set_source_rgba(*vb.rgba(source))
    ctx.fill()


def grain(cv, alpha, seed=1, w=None, h=None, dx=0.0, dy=0.0):
    """Film/paper grain, soft-light over whatever is under the current clip.
    `dx`/`dy` slide the texture, so a grain that changes every frame reads as
    live film rather than a dirty lens."""
    ctx = cv.ctx
    pat = vb.paper_grain(w or cv.width, h or cv.height, seed=seed)
    if dx or dy:
        m = cairo.Matrix()
        m.translate(dx, dy)
        pat.set_matrix(m)
    ctx.save()
    ctx.set_source(pat)
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def vignette(cv, box, strength=0.55):
    """Darkened edges, a lens's falloff, over `box`."""
    ctx = cv.ctx
    r = math.hypot(box.w, box.h) / 2
    ctx.save()
    ctx.rectangle(*box)
    ctx.set_source(radial(ctx, box.cx, box.cy, r, [(0.45, (0, 0, 0, 0)), (1.0, (0, 0, 0, strength))]))
    ctx.fill()
    ctx.restore()


def cover_image(cv, img, box, zoom=1.0, fx=0.5, fy=0.5, radius=0, alpha=1.0):
    """`img` cover-fitted into `box` (never stretched), zoomed by `zoom` about
    the image point (fx, fy) in 0-1 fractions, which is kept as near the box
    centre as the crop allows: the image always covers the box."""
    box = Box(*box)
    s = max(box.w / img.w, box.h / img.h) * zoom
    dw, dh = img.w * s, img.h * s
    x = box.cx - fx * dw
    y = box.cy - fy * dh
    x = min(box.x, max(box.right - dw, x))
    y = min(box.y, max(box.bottom - dh, y))
    with cv.clip(*box, radius):
        cv.image(img, x, y, dw, dh, alpha=alpha)


def fit_lines(copy, width, sizes, weight=800, max_lines=3, tracking=-0.02, balance=True):
    """(font, lines) for `copy` at the largest of `sizes` that wraps to at most
    `max_lines` lines within `width` (the smallest size if none does)."""
    for size in sizes:
        f = kit.font(size, weight, tracking=tracking)
        lines = text.wrap(copy, f, width, balance=balance)
        if len(lines) <= max_lines and text.block_size(lines, f)[0] <= width:
            return f, lines
    return f, lines


def rotated_corners(cx, cy, w, h, angle):
    ca, sa = math.cos(angle), math.sin(angle)
    out = []
    for px, py in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        out.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
    return out


# ---- sample pictures ----

def _canvas(w=PW, h=PH):
    return vb.Canvas(w, h)


def _ridge(rnd, w, base, amp, waves, phase=None):
    """A horizon line: a sum of a few sines, as (x, y) points across the width."""
    phase = phase if phase is not None else [rnd.uniform(0, 6.28) for _ in waves]
    pts = []
    for i in range(0, 121):
        x = w * i / 120
        y = base + sum(a * amp * math.sin(x / w * k * math.pi * 2 + p) for (k, a), p in zip(waves, phase))
        pts.append((x, y))
    return pts


def _layer(ctx, pts, w, h, source):
    poly(ctx, pts + [(w, h + 10), (0, h + 10)])
    fill(ctx, source)


def _dunes():
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    rnd = random.Random(3)
    ctx.rectangle(0, 0, w, h)
    fill(ctx, linear(ctx, 0, 0, 0, h * 0.6, [(0, '#2b1d3f'), (0.55, '#c8665a'), (1, '#f6c58a')]))
    sx, sy = w * 0.64, h * 0.4
    ctx.rectangle(0, 0, w, h)
    fill(ctx, radial(ctx, sx, sy, w * 0.4, [(0, (255, 226, 176, 0.75)), (1, (255, 200, 150, 0))]))
    ctx.arc(sx, sy, w * 0.075, 0, 2 * math.pi)
    fill(ctx, '#ffe6bd')
    tones = (('#d98a5a', '#e6a674'), ('#b8603f', '#d27c52'), ('#8e3f31', '#b25a3c'), ('#5e2627', '#80352d'))
    for i, (dark, light) in enumerate(tones):
        base = h * (0.56 + i * 0.11)
        pts = _ridge(rnd, w, base, h * 0.05 * (1 + i * 0.4), ((1, 0.8), (2.3, 0.35), (4.1, 0.12)))
        _layer(ctx, pts, w, h, linear(ctx, 0, base - h * 0.08, w, base + h * 0.1, [(0, light), (1, dark)]))
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(*vb.rgba('#ffd9a8', 0.35 - i * 0.06))
        ctx.set_line_width(2.5)
        ctx.stroke()
    grain(cv, 0.35, seed=5, w=w, h=h)
    return to_image(cv)


def _harbor():
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    rnd = random.Random(8)
    sea = h * 0.66
    ctx.rectangle(0, 0, w, sea)
    fill(ctx, linear(ctx, 0, 0, 0, sea, [(0, '#070d22'), (0.6, '#17305a'), (1, '#4b6a93')]))
    for _ in range(140):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, sea * 0.6), rnd.uniform(0.6, 1.9)
        ctx.arc(x, y, r, 0, 2 * math.pi)
        fill(ctx, (255, 245, 225, rnd.uniform(0.3, 0.9)))
    mx, my = w * 0.2, h * 0.17
    ctx.arc(mx, my, 44, 0, 2 * math.pi)
    fill(ctx, '#f3ecd8')
    ctx.arc(mx + 18, my - 10, 40, 0, 2 * math.pi)
    fill(ctx, '#0b1530')
    x = -10
    lights = []
    while x < w:
        bw = rnd.uniform(46, 120)
        bh = rnd.uniform(70, 280) * (1.25 if w * 0.45 < x < w * 0.75 else 1.0)
        top = sea - bh
        tone = rnd.choice(('#0c1424', '#111b2e', '#0a111e'))
        ctx.rectangle(x, top, bw, bh)
        fill(ctx, tone)
        for wy in range(int(top + 14), int(sea - 12), 18):
            for wx in range(int(x + 8), int(x + bw - 10), 14):
                if rnd.random() < 0.32:
                    col = rnd.choice(('#ffd27a', '#ffc35c', '#bfe3ff'))
                    ctx.rectangle(wx, wy, 6, 9)
                    fill(ctx, col)
                    lights.append((wx, col))
        x += bw + rnd.uniform(-6, 10)
    ctx.rectangle(0, sea, w, h - sea)
    fill(ctx, linear(ctx, 0, sea, 0, h, [(0, '#1b2e4f'), (1, '#050912')]))
    for wx, col in lights[::2]:
        for k in range(4):
            y = sea + 10 + k * rnd.uniform(14, 40)
            ctx.rectangle(wx + rnd.uniform(-8, 8), y, rnd.uniform(8, 26), 2.5)
            r, g, b, _ = vb.rgba(col)
            fill(ctx, (r * 255, g * 255, b * 255, 0.45 - k * 0.09))
    grain(cv, 0.3, seed=9, w=w, h=h)
    return to_image(cv)


def _forest():
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    rnd = random.Random(21)
    ctx.rectangle(0, 0, w, h)
    fill(ctx, linear(ctx, 0, 0, 0, h * 0.7, [(0, '#e8efe6'), (0.6, '#b9d6cc'), (1, '#86b3a6')]))
    tones = ('#9cc2b6', '#6e9f93', '#467b70', '#2a5850')
    for i, tone in enumerate(tones):
        base = h * (0.42 + i * 0.07)
        pts = []
        x = 0
        y = base
        while x <= w + 40:
            pts.append((x, y))
            x += rnd.uniform(30, 90)
            y = base + rnd.uniform(-1, 1) * h * (0.09 - i * 0.012)
        _layer(ctx, pts, w, h, tone)
        # haze between ranges
        ctx.rectangle(0, base - h * 0.05, w, h * 0.2)
        fill(ctx, linear(ctx, 0, base - h * 0.05, 0, base + h * 0.15, [(0, (232, 240, 234, 0)), (1, (232, 240, 234, 0.35))]))
    lake = h * 0.74
    ctx.rectangle(0, lake, w, h - lake)
    fill(ctx, linear(ctx, 0, lake, 0, h, [(0, '#a9cfc4'), (1, '#3f6f68')]))
    for _ in range(26):
        y = rnd.uniform(lake + 6, h)
        ctx.rectangle(rnd.uniform(0, w), y, rnd.uniform(40, 200), 2)
        fill(ctx, (240, 248, 244, 0.35))
    for side, (x0, x1) in enumerate(((-20, w * 0.3), (w * 0.72, w + 20))):
        x = x0
        while x < x1:
            th = rnd.uniform(160, 330)
            tw = th * rnd.uniform(0.28, 0.36)
            base = lake + rnd.uniform(-4, 10)
            for k in range(4):
                yy = base - th * (0.15 + k * 0.22)
                ww = tw * (1 - k * 0.2)
                poly(ctx, [(x - ww / 2, yy + th * 0.28), (x, yy - th * 0.18), (x + ww / 2, yy + th * 0.28)])
                fill(ctx, '#17352f')
            ctx.rectangle(x - 3, base - th * 0.12, 6, th * 0.12)
            fill(ctx, '#17352f')
            x += tw * rnd.uniform(0.5, 0.8)
    grain(cv, 0.3, seed=12, w=w, h=h)
    return to_image(cv)


def _poster():
    """Not a landscape: a geometric print on a cream wall -- an artwork shot."""
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    cv.fill('#ece3d2')
    ctx.rectangle(0, h * 0.78, w, h * 0.22)
    fill(ctx, '#c9b79a')
    fx, fy, fw, fh = w * 0.3, h * 0.1, w * 0.4, h * 0.62
    cv.shadow(fx, fy, fw, fh, dy=14, blur=30, color=(60, 40, 20, 0.35))
    cv.rect(fx - 14, fy - 14, fw + 28, fh + 28, '#2a2621')
    cv.rect(fx, fy, fw, fh, '#f6f1e6')
    ctx.arc(fx + fw * 0.5, fy + fh * 0.4, fw * 0.3, 0, 2 * math.pi)
    fill(ctx, kit.ACCENT)
    ctx.new_path()
    ctx.arc(fx + fw * 0.5, fy + fh * 0.82, fw * 0.36, math.pi, 2 * math.pi)
    ctx.close_path()
    fill(ctx, kit.TEAL)
    cv.rect(fx + fw * 0.12, fy + fh * 0.62, fw * 0.76, fh * 0.035, '#1d1b18')
    for i in range(5):
        for j in range(3):
            ctx.arc(fx + fw * (0.16 + i * 0.17), fy + fh * (0.09 + j * 0.05), 4, 0, 2 * math.pi)
            fill(ctx, '#1d1b18')
    # a plant and a lamp beside it
    for i, (lx, lh) in enumerate(((w * 0.12, 0.44), (w * 0.84, 0.3))):
        cv.rect(lx - 40, h * 0.78 - 90, 80, 90, '#8c5a3c' if i == 0 else '#3a3a3a', radius=8)
        if i == 0:
            rnd = random.Random(4)
            for k in range(9):
                a = math.radians(-150 + k * 15 + rnd.uniform(-6, 6))
                L = h * lh * rnd.uniform(0.6, 1)
                poly(ctx, [(lx - 6, h * 0.78 - 88), (lx + math.cos(a) * L * 0.55 - 22, h * 0.78 - 88 + math.sin(a) * L * 0.55),
                           (lx + math.cos(a) * L, h * 0.78 - 88 + math.sin(a) * L),
                           (lx + math.cos(a) * L * 0.55 + 22, h * 0.78 - 88 + math.sin(a) * L * 0.55), (lx + 6, h * 0.78 - 88)])
                fill(ctx, '#4f7a4a' if k % 2 else '#3b6338')
        else:
            cv.rect(lx - 3, h * 0.78 - 90 - h * 0.3, 6, h * 0.3, '#3a3a3a')
            poly(ctx, [(lx - 70, h * 0.3), (lx + 70, h * 0.3), (lx + 40, h * 0.18), (lx - 40, h * 0.18)])
            fill(ctx, '#e9c46a')
            ctx.rectangle(0, 0, w, h)
            fill(ctx, radial(ctx, lx, h * 0.34, w * 0.35, [(0, (255, 225, 160, 0.35)), (1, (255, 225, 160, 0))]))
    grain(cv, 0.4, seed=14, w=w, h=h)
    return to_image(cv)


def _fields():
    """Aerial: farm strips on a diagonal, a road, a few trees."""
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    rnd = random.Random(31)
    cv.fill('#7f9a4d')
    ctx.save()
    ctx.translate(w / 2, h / 2)
    ctx.rotate(math.radians(-24))
    tones = ('#a8b85c', '#d9c06a', '#6f8f45', '#c79a52', '#94ad5a', '#e3cf88', '#5f7f3f', '#b5884a')
    y = -h * 1.1
    i = 0
    while y < h * 1.1:
        bh = rnd.uniform(60, 150)
        tone = tones[i % len(tones)]
        ctx.rectangle(-w, y, w * 2, bh)
        fill(ctx, tone)
        for k in range(int(bh // 9)):
            ctx.rectangle(-w, y + 4 + k * 9, w * 2, 2)
            fill(ctx, (0, 0, 0, 0.07))
        y += bh
        i += 1
    ctx.restore()
    ctx.new_path()
    ctx.move_to(w * 0.08, -20)
    ctx.curve_to(w * 0.4, h * 0.4, w * 0.5, h * 0.55, w * 1.05, h * 0.92)
    ctx.set_source_rgba(*vb.rgba('#e9e4d6'))
    ctx.set_line_width(22)
    ctx.stroke()
    for _ in range(40):
        x, y2, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(10, 22)
        ctx.arc(x + r * 0.5, y2 + r * 0.6, r, 0, 2 * math.pi)
        fill(ctx, (20, 30, 10, 0.35))
        ctx.arc(x, y2, r, 0, 2 * math.pi)
        fill(ctx, rnd.choice(('#2f5a2c', '#3c6b33', '#284d27')))
    grain(cv, 0.35, seed=16, w=w, h=h)
    return to_image(cv)


def _coast():
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    rnd = random.Random(44)
    sea = h * 0.55
    ctx.rectangle(0, 0, w, sea)
    fill(ctx, linear(ctx, 0, 0, 0, sea, [(0, '#5b8fb9'), (0.7, '#f2c6a0'), (1, '#ffdcb8')]))
    ctx.arc(w * 0.7, sea - 4, 70, math.pi, 2 * math.pi)
    fill(ctx, '#fff1d9')
    ctx.rectangle(0, sea, w, h - sea)
    fill(ctx, linear(ctx, 0, sea, 0, h, [(0, '#2e6f95'), (1, '#0f3550')]))
    for _ in range(70):
        y = sea + (rnd.random() ** 2) * (h - sea)
        ln = rnd.uniform(20, 120) * (1 + (y - sea) / h * 2)
        ctx.rectangle(w * 0.7 + rnd.gauss(0, 120) - ln / 2, y, ln, 2.5)
        fill(ctx, (255, 230, 200, 0.5))
    cliff = [(-10, h * 0.38), (w * 0.14, h * 0.36), (w * 0.24, h * 0.42), (w * 0.33, h * 0.56), (w * 0.38, h * 0.8),
             (w * 0.46, h + 10), (-10, h + 10)]
    poly(ctx, cliff)
    fill(ctx, linear(ctx, 0, h * 0.36, w * 0.4, h, [(0, '#5b4a3a'), (1, '#2b2119')]))
    poly(ctx, [(-10, h * 0.385), (w * 0.14, h * 0.365), (w * 0.24, h * 0.425), (w * 0.2, h * 0.44), (-10, h * 0.42)])
    fill(ctx, '#4f7a4a')
    lx, ly = w * 0.12, h * 0.37
    poly(ctx, [(lx - 16, ly), (lx + 16, ly), (lx + 10, ly - 120), (lx - 10, ly - 120)])
    fill(ctx, '#f4efe6')
    ctx.rectangle(lx - 14, ly - 70, 28, 20)
    fill(ctx, kit.ACCENT)
    cv.rect(lx - 14, ly - 146, 28, 26, '#fff4c9')
    poly(ctx, [(lx - 16, ly - 146), (lx + 16, ly - 146), (lx, ly - 168)])
    fill(ctx, kit.ACCENT)
    poly(ctx, [(lx, ly - 134), (w * 0.62, ly - 220), (w * 0.62, ly - 120)])
    fill(ctx, linear(ctx, lx, 0, w * 0.62, 0, [(0, (255, 244, 201, 0.55)), (1, (255, 244, 201, 0))]))
    grain(cv, 0.22, seed=18, w=w, h=h)
    return to_image(cv)


def _valley(after):
    """One valley, twice: `after` False is a grey, bare winter; True the same
    place in late spring. Same geometry, so a wipe between them lines up."""
    cv = _canvas()
    ctx, w, h = cv.ctx, PW, PH
    if after:
        sky = [(0, '#3d7cb8'), (0.65, '#f4c590'), (1, '#ffe2b3')]
        hills = ('#9ec26a', '#6fa04d', '#4d8a3b', '#356e2e')
    else:
        sky = [(0, '#8d949c'), (0.65, '#b9bcbf'), (1, '#c9cacb')]
        hills = ('#a3a59f', '#8e918a', '#7b7e78', '#686b66')
    ctx.rectangle(0, 0, w, h)
    fill(ctx, linear(ctx, 0, 0, 0, h * 0.62, sky))
    if after:
        ctx.rectangle(0, 0, w, h)
        fill(ctx, radial(ctx, w * 0.78, h * 0.36, w * 0.45, [(0, (255, 230, 180, 0.7)), (1, (255, 230, 180, 0))]))
        ctx.arc(w * 0.78, h * 0.36, 52, 0, 2 * math.pi)
        fill(ctx, '#fff0cf')
    rnd = random.Random(52)
    phases = [[rnd.uniform(0, 6.28) for _ in range(3)] for _ in hills]
    ridges = []
    for i, tone in enumerate(hills):
        base = h * (0.5 + i * 0.1)
        pts = _ridge(rnd, w, base, h * 0.05, ((0.8, 1.0), (1.7, 0.4), (3.3, 0.15)), phase=phases[i])
        ridges.append(pts)
        _layer(ctx, pts, w, h, tone)
    # the cottage on the second ridge
    hx = w * 0.34
    hy = min(y for x, y in ridges[1] if abs(x - hx) < 60) + 8
    cv.rect(hx - 70, hy - 80, 140, 84, '#efe6d6' if after else '#b4b0a8')
    poly(ctx, [(hx - 86, hy - 78), (hx, hy - 150), (hx + 86, hy - 78)])
    fill(ctx, '#b8573c' if after else '#6d6a66')
    for wx in (hx - 46, hx + 18):
        cv.rect(wx, hy - 58, 28, 26, '#ffd27a' if after else '#7c7f82')
    cv.rect(hx - 12, hy - 40, 24, 44, '#6b4630' if after else '#5f5c58')
    # the tree on the near ridge
    tx = w * 0.7
    ty = min(y for x, y in ridges[3] if abs(x - tx) < 40) + 10
    cv.rect(tx - 9, ty - 170, 18, 172, '#5b4030' if after else '#4c4945')
    if after:
        for dx, dy, r in ((-60, -190, 70), (50, -200, 76), (-5, -250, 84), (0, -170, 64)):
            ctx.arc(tx + dx, ty + dy, r, 0, 2 * math.pi)
            fill(ctx, '#3f7d35')
        for dx, dy, r in ((-40, -230, 40), (40, -240, 36)):
            ctx.arc(tx + dx, ty + dy, r, 0, 2 * math.pi)
            fill(ctx, '#5c9b45')
        for _ in range(160):
            x, y = rnd.uniform(0, w), rnd.uniform(h * 0.78, h)
            ctx.arc(x, y, rnd.uniform(2, 4.5), 0, 2 * math.pi)
            fill(ctx, rnd.choice(('#ffe36e', '#ffffff', '#ef8a7c', '#f6b8d0')))
    else:
        ctx.set_source_rgba(*vb.rgba('#4c4945'))
        for a, L in ((-120, 120), (-60, 130), (-95, 150), (-140, 80), (-35, 90)):
            r = math.radians(a)
            ctx.move_to(tx, ty - 150)
            ctx.line_to(tx + math.cos(r) * L, ty - 150 + math.sin(r) * L)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.rectangle(0, 0, w, h)
        fill(ctx, (200, 204, 208, 0.18))
    grain(cv, 0.35, seed=22, w=w, h=h)
    return to_image(cv)


SCENES = {'dunes': _dunes, 'harbor': _harbor, 'forest': _forest, 'poster': _poster, 'fields': _fields,
          'coast': _coast, 'before': lambda: _valley(False), 'after': lambda: _valley(True)}


@lru_cache(maxsize=None)
def photo(name):
    """The sample picture `name` (one of `SCENES`), built once."""
    return SCENES[name]()


# ---- a sample app screenshot ----

SCREEN_W, SCREEN_H = 780, 1688  # a tall phone screen at 2x


@lru_cache(maxsize=None)
def app_screen():
    """A tall phone screenshot of a made-up trip planner, light theme: status
    bar, header, a hero photo card, three stat tiles, a list, a tab bar."""
    w, h = SCREEN_W, SCREEN_H
    cv = vb.Canvas(w, h)
    ctx = cv.ctx
    dark, muted, card, line = '#1c1e25', '#7b818d', '#ffffff', '#e3e5ea'
    cv.fill('#f4f3ef')
    text.draw(cv, '9:41', kit.font(30, 700), 56, 28, dark)
    for i in range(4):
        cv.rect(w - 170 + i * 14, 50 - i * 6, 9, 12 + i * 6, dark, radius=2)
    cv.outline(w - 104, 34, 52, 26, dark, width=2.5, radius=7)
    cv.rect(w - 99, 39, 34, 16, dark, radius=4)
    text.draw(cv, 'Good morning', kit.font(30, 500), 56, 128, muted)
    text.draw(cv, 'Your trips', kit.font(68, 800, tracking=-0.02), 56, 168, dark)
    ctx.arc(w - 96, 214, 40, 0, 2 * math.pi)
    fill(ctx, kit.TEAL)
    text.draw(cv, 'MK', kit.font(28, 800), w - 136, 196, '#ffffff', align='center', width=80)
    # hero card
    hx, hy, hw, hh = 40, 290, w - 80, 520
    cv.shadow(hx, hy, hw, hh, radius=36, dy=14, blur=30, color=(30, 30, 40, 0.18))
    cover_image(cv, photo('forest'), (hx, hy, hw, hh), zoom=1.15, fx=0.42, radius=36)
    with cv.clip(hx, hy, hw, hh, 36):
        ctx.rectangle(hx, hy + hh * 0.4, hw, hh * 0.6)
        fill(ctx, linear(ctx, 0, hy + hh * 0.4, 0, hy + hh, [(0, (0, 0, 0, 0)), (1, (10, 30, 26, 0.7))]))
    cv.rect(hx + 32, hy + 32, 180, 52, '#ffffff', radius=26)
    text.draw(cv, 'In 12 days', kit.font(26, 700), hx + 32, hy + 42, dark, align='center', width=180)
    text.draw(cv, 'Lakeside weekend', kit.font(52, 800, tracking=-0.02), hx + 36, hy + hh - 150, '#ffffff')
    text.draw(cv, '3 nights · 2 travellers', kit.font(30, 500), hx + 36, hy + hh - 80, '#e7efe9')
    # stat tiles
    ty, th = hy + hh + 40, 200
    tw = (w - 80 - 2 * 24) / 3
    for i, (label, value, col) in enumerate((('Budget', '$840', kit.ACCENT), ('Packed', '18/24', kit.TEAL),
                                             ('Drive', '2h 40', '#e9b44c'))):
        x = 40 + i * (tw + 24)
        cv.rect(x, ty, tw, th, card, radius=28)
        cv.outline(x, ty, tw, th, line, width=2, radius=28)
        cv.rect(x + 28, ty + 30, 44, 8, col, radius=4)
        text.draw(cv, label, kit.font(26, 600), x + 28, ty + 58, muted)
        text.draw(cv, value, kit.mono(48, 700), x + 28, ty + 104, dark)
    # list
    ly = ty + th + 56
    text.draw(cv, 'Ideas for later', kit.font(36, 800), 56, ly, dark)
    ly += 70
    for i, (name, sub, scene) in enumerate((('Desert stargazing', 'Open dates in spring', 'dunes'),
                                            ('Old harbour by night', 'A 2-day city break', 'harbor'),
                                            ('Lighthouse coast', 'Walks and seafood', 'coast'))):
        y = ly + i * 150
        cover_image(cv, photo(scene), (56, y, 120, 120), radius=24)
        text.draw(cv, name, kit.font(34, 700), 204, y + 22, dark)
        text.draw(cv, sub, kit.font(28, 500), 204, y + 70, muted)
        if i:
            cv.rect(204, y - 15, w - 260, 2, line)
    # tab bar
    cv.rect(0, h - 150, w, 150, '#ffffff')
    cv.rect(0, h - 150, w, 2, line)
    for i in range(4):
        cx = w * (i + 0.5) / 4
        cv.rect(cx - 22, h - 116, 44, 44, kit.ACCENT if i == 0 else '#c7cad1', radius=12)
    cv.rect(w / 2 - 110, h - 22, 220, 8, dark, radius=4)
    return to_image(cv)

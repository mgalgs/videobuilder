"""Title: extruded 3D. The title as solid block letters standing on a floor
grid: real glyph outlines, extruded in depth and projected through a
perspective camera, swing round from edge-on into a three-quarter view on a
spring, the accent-coloured sides catching the light while the face stays
bright. Once settled the camera keeps drifting a few degrees, so the depth
keeps reading. An optional subtitle settles flat under the floor line.

No pre-rendered clip: the letters are Pango's own outlines
(`PangoCairo.layout_path`), flattened once and projected per frame, so any
title works. A tall frame wraps the title into more, bigger lines and the
floor grid runs down into the lower half.
"""
import math
from functools import lru_cache

import cairo
from gi.repository import PangoCairo

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from ._title_util import fit, frames_per_beat

FOCAL = 1100.0
SLICES = 28
SUB_F = kit.font(26, 500)
PAD = 44
SETTLE_YAW, SETTLE_PITCH = -30.0, 16.0
DRIFT = 5.0
BOUNCY = vb.damped(0.55, hz=1.6)


def _font(size):
    return kit.font(size, 900, tracking=-0.02)


@lru_cache(maxsize=32)
def _outline(lines, font):
    """Every glyph contour of the centred block as a list of point lists, in
    px about the block's centre, plus the block's (w, h)."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
    ctx = cairo.Context(surf)
    lh = text.line_height(font)
    bw, bh = text.block_size(lines, font)
    for i, line in enumerate(lines):
        w = text.measure(line, font)
        layout = text._layout(ctx, line, font)
        content, _ = text._content(font)
        ctx.move_to(-w / 2, -bh / 2 + i * lh + (lh - content) / 2)
        PangoCairo.layout_path(ctx, layout)
    contours, cur = [], []
    for kind, pts in ctx.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            if len(cur) > 2:
                contours.append(cur)
            cur = [pts]
        elif kind == cairo.PATH_LINE_TO:
            cur.append(pts)
        elif kind == cairo.PATH_CLOSE_PATH:
            if len(cur) > 2:
                contours.append(cur)
            cur = []
    if len(cur) > 2:
        contours.append(cur)
    return tuple(tuple(c) for c in contours), (bw, bh)


class Camera:
    def __init__(self, cx, cy, yaw, pitch, scale):
        self.cx, self.cy, self.k = cx, cy, scale
        self.cy_, self.sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        self.cp, self.sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def project(self, x, y, z):
        x, y, z = x * self.k, y * self.k, z * self.k
        x1 = x * self.cy_ + z * self.sy_
        z1 = -x * self.sy_ + z * self.cy_
        y2 = y * self.cp - z1 * self.sp
        z2 = y * self.sp + z1 * self.cp
        d = FOCAL / max(80.0, FOCAL + z2)
        return self.cx + x1 * d, self.cy + y2 * d, z2


def _fill(ctx, polys):
    ctx.new_path()
    for poly in polys:
        ctx.move_to(*poly[0])
        for p in poly[1:]:
            ctx.line_to(*p)
        ctx.close_path()
    ctx.fill()


def _bbox(cam, contours, depth):
    xs, ys = [], []
    for c in contours:
        for x, y in c[::3]:
            for z in (0, depth):
                px, py, _ = cam.project(x, y, z)
                xs.append(px)
                ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


def _layout(cv, title, has_sub):
    s = vb.Box.of(cv).pad(PAD)
    tall = cv.height > cv.width * 1.2
    sub_room = text.line_height(SUB_F) * 2 + 40 if has_sub else 0
    max_w = s.w * (0.8 if tall else 0.72)
    max_h = (s.h - sub_room) * (0.5 if tall else 0.62)
    for size in range(170, 27, -4):
        f = _font(size)
        lines = text.wrap(title.upper(), f, max_w, balance=True)
        bw, bh = text.block_size(lines, f)
        if bw <= max_w and bh <= max_h and all(text.measure(ln, f) <= max_w for ln in lines):
            break
    contours, (bw, bh) = _outline(tuple(lines), f)
    depth = size * 0.62
    cy = s.y + (s.h - sub_room) * (0.44 if tall else 0.47)
    # Scale the whole object so its widest pose (settled, plus the drift) stays inside the safe area.
    k = 1.0
    for _ in range(3):
        boxes = [_bbox(Camera(s.cx, cy, SETTLE_YAW + d, SETTLE_PITCH, k), contours, depth) for d in (-DRIFT, DRIFT)]
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes)
        y1 = max(b[3] for b in boxes)
        fit = min(1.0, (s.w - 8) / (x1 - x0), (s.h - sub_room - 8) / (y1 - y0))
        if fit >= 0.999:
            break
        k *= fit
    return s, size, contours, (bw, bh), depth, cy, k, y1


def _floor(cv, cam, y_floor, size, accent, fade):
    ctx = cv.ctx
    grid = kit.mix('#3a3d47', accent, 0.35)
    step = size * 0.9
    span = 14
    ctx.set_line_width(1.2)
    for i in range(-span, span + 1):
        x = i * step
        a = cam.project(x, y_floor, -step * 2)
        b = cam.project(x, y_floor, step * 18)
        g = cairo.LinearGradient(a[0], a[1], b[0], b[1])
        g.add_color_stop_rgba(0, *vb.rgba(grid, 0.9 * fade))
        g.add_color_stop_rgba(1, *vb.rgba(grid, 0.0))
        ctx.set_source(g)
        ctx.move_to(a[0], a[1])
        ctx.line_to(b[0], b[1])
        ctx.stroke()
    for j in range(-2, 18):
        z = j * step
        a = cam.project(-span * step, y_floor, z)
        b = cam.project(span * step, y_floor, z)
        alpha = max(0.0, 1 - (j + 2) / 20) * 0.9 * fade
        ctx.set_source_rgba(*vb.rgba(grid, alpha))
        ctx.move_to(a[0], a[1])
        ctx.line_to(b[0], b[1])
        ctx.stroke()


def draw(cv, shot):
    data = shot.data
    accent = data['accent']
    fpb = frames_per_beat(shot)
    n = shot.f
    cv.fill(kit.BG)
    s, size, contours, (bw, bh), depth, cy, k, title_bottom = _layout(cv, data['title'], bool(data['subtitle']))
    ctx = cv.ctx

    # The swing: edge-on to three-quarter on a spring, landing on the second beat; then a slow drift.
    p = vb.spring_at(n - 2, 30, **BOUNCY)
    drift = DRIFT * math.sin(2 * math.pi * max(0.0, n - fpb * 2) / (fpb * 8))
    yaw = -82 + (SETTLE_YAW + 82) * p + drift * vb.clamp01((n - fpb * 1.5) / fpb)
    pitch = 28 + (SETTLE_PITCH - 28) * p
    cam = Camera(s.cx, cy, yaw, pitch, k)

    # A pool of light behind the letters.
    g = cairo.RadialGradient(s.cx, cy, 10, s.cx, cy, max(cv.width, cv.height) * 0.6)
    g.add_color_stop_rgba(0, *vb.rgba(accent, 0.16))
    g.add_color_stop_rgba(1, *vb.rgba(accent, 0.0))
    ctx.set_source(g)
    ctx.paint()

    y_floor = bh / 2 + size * 0.06
    _floor(cv, cam, y_floor, size, accent, vb.clamp01(n / fpb))

    # A contact shadow on the floor, under the letters.
    sh = [cam.project(x, y_floor, z)[:2] for x, z in
          ((-bw / 2, 0), (bw / 2, 0), (bw / 2 + size * 0.3, depth + size * 0.8), (-bw / 2 + size * 0.3, depth + size * 0.8))]
    cv.shape_shadow(sh, blur=round(size * 0.3), color=(0, 0, 0, 0.55 * vb.clamp01(p)))

    # The extrusion, back slice first: dark accent at the back, lit accent at the front.
    proj = [[[cam.project(x, y, 0)[:2] for x, y in c]] for c in contours]
    if p > 0.02:
        for i in range(SLICES, 0, -1):
            z = depth * i / SLICES
            shade = 0.2 + 0.7 * (1 - i / SLICES) ** 1.5
            col = kit.mix(kit.BG, accent, shade)
            ctx.set_source_rgba(col[0] / 255, col[1] / 255, col[2] / 255, 1)
            _fill(ctx, [[cam.project(x, y, z)[:2] for x, y in c] for c in contours])
    # The face: bright, with a soft top light.
    x0, y0, x1, y1 = _bbox(cam, contours, 0)
    face = cairo.LinearGradient(0, y0, 0, y1)
    face.add_color_stop_rgba(0, *vb.rgba('#ffffff'))
    face.add_color_stop_rgba(1, *vb.rgba(kit.mix(kit.INK, accent, 0.18)))
    ctx.set_source(face)
    _fill(ctx, [c[0] for c in proj])
    ctx.new_path()
    for c in proj:
        ctx.move_to(*c[0][0])
        for pt in c[0][1:]:
            ctx.line_to(*pt)
        ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(kit.mix(accent, kit.BG, 0.35)))
    ctx.set_line_width(max(1.0, size * k * 0.012))
    ctx.stroke()
    bx0, by0, bx1, by1 = _bbox(cam, contours, depth)
    cv.mark('title', bx0, by0, bx1 - bx0, by1 - by0)

    sub = data['subtitle']
    if sub:
        sf, lines = fit(sub, lambda sz: kit.font(sz, 500), s.w * 0.9, text.line_height(SUB_F) * 2,
                        tuple(range(26, 11, -1)))
        sw, shh = text.block_size(lines, sf)
        q = vb.clamp01(vb.spring_at(n - fpb * 1.5, 30, **vb.damped(0.8, hz=2.5)))
        top = min(s.bottom - shh, max(title_bottom + 28, s.y + (s.h - shh) * 0.8))
        with cv.layer(opacity=q, dy=(1 - q) * 18):
            box = text.draw(cv, lines, sf, s.cx - sw / 2, top, kit.MUTED, align='center', width=sw)
        if q > 0.01:
            cv.mark('subtitle', *box)


COMPONENT = Component(
    id='extruded-3d-title',
    kind='title',
    description=('The title as solid 3D block letters on a perspective floor grid: they swing round from edge-on '
                 'into a three-quarter view on a spring, accent-coloured sides, then keep drifting gently.'),
    tags=('title', '3d', 'depth', 'extruded', 'hero', 'bold', 'orbit'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('title', 'text', True, 'One to three short words; set as solid block letters.', max_length=20),
        Slot('subtitle', 'text', False, 'One quiet line under the floor.', max_length=48),
        Slot('accent', 'color', False, 'Colour of the letters\' extruded sides and the glow behind them.'),
    ),
    sample={'title': 'Go deeper', 'subtitle': 'A season of long reads, out every Friday', 'accent': kit.ACCENT},
    draw=draw,
)

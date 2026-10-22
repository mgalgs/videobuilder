"""Liquify: a round brush drags across the picture and the pixels under it
go with it, smeared along the stroke like wet paint pushed by a finger, while
everything outside the brush stays put."""
import math

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _pixels(cv, draw):
    """`draw(c)` on a fresh canvas the size and scale of `cv`, as a PIL RGB image."""
    c = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(c)
    s = c.surface
    s.flush()
    im = Image.frombuffer('RGBA', (s.get_width(), s.get_height()), bytes(s.get_data()), 'raw', 'BGRA',
                          s.get_stride(), 1)
    return im.convert('RGB')


def _point_at(stroke, d):
    """The point distance `d` along the polyline `stroke`."""
    for (x0, y0), (x1, y1) in zip(stroke, stroke[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if d <= seg and seg > 0:
            k = d / seg
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        d -= seg
    return stroke[-1]


def _length(stroke):
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(stroke, stroke[1:]))


def brush_at(stroke, p):
    """Where the brush is at progress `p` (0 -> 1) along `stroke`."""
    return _point_at(stroke, _length(stroke) * vb.clamp01(p))


def dabs(stroke, p, radius, spacing=0.12):
    """The brush's pushes so far: (x, y, dx, dy) for each small step along
    the first `p` of `stroke`, `spacing` x `radius` apart."""
    total = _length(stroke) * vb.clamp01(p)
    step = max(1e-6, radius * spacing)
    n = math.ceil(total / step)
    out = []
    prev = stroke[0]
    for i in range(1, n + 1):
        cur = _point_at(stroke, min(total, i * step))
        out.append((prev[0], prev[1], cur[0] - prev[0], cur[1] - prev[1]))
        prev = cur
    return out


def liquify(im, pushes, radius, strength=1.0, cells=96):
    """`im` (PIL) pushed by a liquify brush of `radius` px: each push
    (x, y, dx, dy) carries the pixels near (x, y) by (dx, dy) x `strength`,
    fully at the centre and fading smoothly to nothing at the rim, applied in
    order so a run of pushes along a path smears the picture along it. A mesh
    warp of `cells` across; points pushed past the edge pick up the edge."""
    w, h = im.size
    if not pushes or strength == 0:
        return im
    nx = cells
    ny = max(1, round(cells * h / w))
    r2 = radius * radius

    def fall(x, y, cx, cy):
        q = ((x - cx) ** 2 + (y - cy) ** 2) / r2
        return 0.0 if q >= 1 else (1 - q) ** 2

    near = [(x, y, dx * strength, dy * strength) for x, y, dx, dy in pushes]
    reach = radius + max(math.hypot(dx, dy) for _, _, dx, dy in near)

    def src(x, y):
        # Undo the pushes newest first: each moved y to y + d*fall(y), so solve for y by iteration.
        for cx, cy, dx, dy in reversed(near):
            if abs(x - cx) > reach or abs(y - cy) > reach:
                continue
            sx, sy = x, y
            for _ in range(4):
                f = fall(sx, sy, cx, cy)
                sx, sy = x - dx * f, y - dy * f
            x, y = sx, sy
        return min(max(x, 0), w - 1), min(max(y, 0), h - 1)

    xs = [w * i / nx for i in range(nx + 1)]
    ys = [h * j / ny for j in range(ny + 1)]
    grid = [[src(x, y) for x in xs] for y in ys]
    mesh = []
    for j in range(ny):
        for i in range(nx):
            box = (round(xs[i]), round(ys[j]), round(xs[i + 1]), round(ys[j + 1]))
            (ax, ay), (bx, by) = grid[j][i], grid[j + 1][i]
            (qx, qy), (dx, dy) = grid[j + 1][i + 1], grid[j][i + 1]
            mesh.append((box, (ax, ay, bx, by, qx, qy, dx, dy)))
    return im.transform((w, h), Image.MESH, mesh, Image.BILINEAR)


def push_warp(cv, draw, stroke, p, radius=90, strength=1.0, cells=96):
    """Draw `draw(cv)` smeared by a liquify brush that has travelled the
    first `p` (0 -> 1) of `stroke` (a list of (x, y) film px), `radius` film
    px wide. Returns the brush centre, for drawing a cursor over it.

    In a film, e.g. `push_warp(cv, lambda c: scene(c, t), [(800, 300), (760, 520)], ease(p))`."""
    s = cv.scale
    pts = [(x * s, y * s) for x, y in stroke]
    out = liquify(_pixels(cv, draw), dabs(pts, p, radius * s), radius * s, strength, cells)
    data = bytearray(out.tobytes('raw', 'BGRX'))
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_RGB24, out.width, out.height, out.width * 4)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(surf, 0, 0)
    c.paint()
    c.restore()
    return brush_at(stroke, p)


# ---- demo ----

_STROKE = [(640, 190), (650, 260), (640, 330), (610, 400)]
_RADIUS = 80


def _rgb(hexs):
    hexs = hexs.lstrip('#')
    return tuple(int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _scene(cv):
    W, H = demo.W, demo.H
    c = cv.ctx
    sky = cairo.LinearGradient(0, 0, 0, H * 0.7)
    sky.add_color_stop_rgb(0, *_rgb('#2b2f5e'))
    sky.add_color_stop_rgb(1, *_rgb('#8c90f0'))
    c.set_source(sky)
    c.rectangle(0, 0, W, H)
    c.fill()
    demo.dot(cv, 640, 190, r=62, color='#f2b705')
    for y0, amp, freq, ph, col in ((330, 50, 1.3, 0.4, '#6670a8'), (380, 40, 1.8, 2.1, '#3f4770'),
                                   (450, 30, 1.1, 4.0, '#252a40')):
        c.move_to(0, H)
        for i in range(97):
            x = W * i / 96
            c.line_to(x, y0 - amp * math.sin(freq * x / W * 2 * math.pi + ph))
        c.line_to(W, H)
        c.close_path()
        c.set_source_rgb(*_rgb(col))
        c.fill()


def _draw(n, cv):
    p = demo.phase(n, 0.4, 2.4)
    p = p * p * (3 - 2 * p)
    bx, by = push_warp(cv, _scene, _STROKE, p, radius=_RADIUS)
    if 0 < demo.phase(n, 0.15, 2.7) < 1:
        cv.arc(bx, by, _RADIUS, 0, 2 * math.pi, demo.INK, width=2, alpha=0.8)


TECHNIQUE = Technique(
    id='liquify',
    name='Liquify',
    family='vfx',
    group='Distortion & displacement',
    aliases=('push warp', 'smear warp', 'fluid warp', 'forward warp'),
    definition='A round brush drags through the image and carries the pixels beneath it along its path, '
               'smudging shapes like a finger through wet paint.',
    phrasings=('smudge the sun down into the hills like wet paint',
               'drag part of the picture with a brush so it stretches and smears',
               'push the pixels around as if the image were liquid'),
    related=('pixelate-transition', 'gradient-wipe', 'gaussian-blur', 'blur-dissolve', 'domain-warping',
             'pixelation'),
    api=('videobuilder.techniques.vfx.liquify.push_warp',
         'videobuilder.techniques.vfx.liquify.liquify',
         'videobuilder.techniques.vfx.liquify.dabs'),
    demo=lambda: demo.film(_draw),
)

"""Chrome reflection: a mirror-finish ball shows the room around it, bent by
its curvature -- a light overhead, a horizon across its middle, coloured
panels on either side squeezed into arcs toward the rim. As the panels
circle the ball, their reflections slide round it, stretching and pinching
as they go."""
import math

import cairo
from PIL import Image, ImageDraw

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ENV_W, ENV_H = 720, 360   # the equirectangular room: 2 px a degree


def environment(panels=(), sky=('#6b717c', '#30343c'), ground=('#0d0e12', '#1d2027'),
                horizon='#aab2c0', light=(0.0, 58.0, 70.0, 26.0), light_color='#f4f6fa'):
    """An equirectangular picture of the room a mirror reflects (a PIL image,
    ENV_W x ENV_H, azimuth -180 -> 180 degrees left to right with 0 toward
    the viewer, elevation 90 -> -90 top to bottom). `sky` and `ground` are
    (far, near-horizon) colours; `horizon` a thin bright line between them.
    `light` is (azimuth, elevation, width, height) in degrees of a soft-box
    overhead, or None. `panels` are (azimuth, bottom, top, width, colour):
    upright strips of colour, angles in degrees."""
    im = Image.new('RGB', (ENV_W, ENV_H))
    d = ImageDraw.Draw(im)
    half = ENV_H // 2
    for y in range(ENV_H):
        if y < half:
            a, b, k = sky[0], sky[1], y / half
        else:
            a, b, k = ground[1], ground[0], (y - half) / half
        ca, cb = vb.rgba(a), vb.rgba(b)
        d.line([(0, y), (ENV_W, y)], fill=tuple(round(255 * (ca[i] + (cb[i] - ca[i]) * k)) for i in range(3)))
    d.rectangle([0, half - 1, ENV_W, half + 1], fill=_rgb(horizon))

    def px(az, el):
        return (az / 360 + 0.5) * ENV_W, (0.5 - el / 180) * ENV_H

    def band(az, bottom, top, width, color):
        x0, y0 = px(az - width / 2, top)
        x1, y1 = px(az + width / 2, bottom)
        for shift in (-ENV_W, 0, ENV_W):   # wrap round the back of the room
            d.rectangle([x0 + shift, y0, x1 + shift, y1], fill=_rgb(color))

    if light:
        az, el, w, h = light
        band(az, el - h / 2, el + h / 2, w, light_color)
    for az, bottom, top, width, color in panels:
        band((az + 180) % 360 - 180, bottom, top, width, color)
    return im


def _rgb(color):
    return tuple(round(255 * c) for c in vb.rgba(color)[:3])


def _reflect(u, v, turn):
    """Where in the room (environment px) the ball's surface at (u, v) --
    unit-disc coordinates, y down -- reflects, seen head-on from far away,
    with the room turned by `turn` degrees."""
    rr = u * u + v * v
    if rr > 0.9995:
        k = math.sqrt(0.9995 / rr)
        u, v, rr = u * k, v * k, 0.9995
    nz = math.sqrt(1 - rr)
    rx, ry, rz = 2 * nz * u, -2 * nz * v, 2 * nz * nz - 1
    az = math.degrees(math.atan2(rx, rz)) - turn
    el = math.degrees(math.asin(max(-1.0, min(1.0, ry))))
    return (az / 360 + 0.5) * ENV_W, (0.5 - el / 180) * ENV_H


def reflect_sphere(env, size, turn=0.0, cells=48):
    """The mirror ball's face as a `size` x `size` PIL image: `env` (an
    equirectangular room, see `environment`) mapped through the reflection
    off a sphere filling the square, the room turned by `turn` degrees.
    The corners outside the disc are filler; clip them to a circle."""
    tiled = Image.new('RGB', (ENV_W * 3, ENV_H))
    for i in range(3):
        tiled.paste(env, (i * ENV_W, 0))
    cells = max(1, min(cells, size // 4))   # a small render gets fewer, still non-empty, cells
    step = size / cells
    mesh = []
    for j in range(cells):
        for i in range(cells):
            x0, y0 = i * step, j * step
            box = (round(x0), round(y0), round(x0 + step), round(y0 + step))
            pts = [_reflect(2 * x / size - 1, 2 * y / size - 1, turn)
                   for x, y in ((box[0], box[1]), (box[0], box[3]), (box[2], box[3]), (box[2], box[1]))]
            xs = [x % ENV_W for x, _ in pts]
            if max(xs) - min(xs) > ENV_W / 2:   # the quad straddles the seam behind the ball
                xs = [x + ENV_W if x < ENV_W / 2 else x for x in xs]
            quad = []
            for x, (_, y) in zip(xs, pts):
                quad += [x + ENV_W, min(ENV_H - 1.0, max(0.0, y))]
            mesh.append((box, quad))
    return tiled.transform((size, size), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR)


def draw_chrome_ball(cv, cx, cy, r, env, turn=0.0, rim='#08090c'):
    """Draw a mirror-finish ball of radius `r` centred at (cx, cy) reflecting
    `env` (see `environment`), the room turned by `turn` degrees -- animate
    `turn`, or rebuild `env` each frame, to make the reflection move. Adds a
    soft darkening toward the rim and a thin dark edge. Returns its Box."""
    size = max(8, round(2 * r * cv.scale_factor()))
    img = vb.Image.from_pil(reflect_sphere(env, size, turn))
    c = cv.ctx
    c.save()
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.clip()
    cv.image(img, cx - r, cy - r, 2 * r, 2 * r)
    g = cairo.RadialGradient(cx, cy, r * 0.55, cx, cy, r)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
    c.set_source(g)
    c.paint()
    c.restore()
    cv.arc(cx, cy, r, 0, 2 * math.pi, rim, width=max(1.0, r * 0.012))
    return vb.Box(cx - r, cy - r, 2 * r, 2 * r)


PANELS = ((demo.ACCENT, 0), (demo.TEAL, 120), ('#f0b429', 240))


def draw(n, cv):
    t = n / demo.FPS
    spin = 150 * demo.phase(n, 0.2, 2.8) - 75 + 10 * math.sin(t)   # degrees the panels have travelled
    cx, cy, r = demo.W / 2, demo.H / 2 - 10, 160
    orbit = 330
    placed = [(color, (base + spin + 180) % 360 - 180) for color, base in PANELS]
    env = environment([(az, -8, 40, 22, color) for color, az in placed])

    floor = cy + r + 18
    g = cairo.RadialGradient(cx, floor, 10, cx, floor, r * 1.1)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.55)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    cv.ctx.save()
    cv.ctx.translate(0, floor)
    cv.ctx.scale(1, 0.12)
    cv.ctx.translate(0, -floor)
    cv.ctx.set_source(g)
    cv.ctx.arc(cx, floor, r * 1.1, 0, 2 * math.pi)
    cv.ctx.fill()
    cv.ctx.restore()

    def panel(color, az):
        a = math.radians(az)
        depth = math.cos(a)                     # 1 = in front of the ball, -1 = behind it
        x = cx + orbit * math.sin(a)
        h = 200 * (1 + 0.12 * depth)
        w = 18 * abs(math.sin(a)) + 3
        cv.rect(x - w / 2, cy + 25 - h, w, h, color, radius=3, alpha=0.55 + 0.45 * (1 + depth) / 2)

    behind = [p for p in placed if math.cos(math.radians(p[1])) < 0]
    front = [p for p in placed if p not in behind]
    for p in behind:
        panel(*p)
    box = draw_chrome_ball(cv, cx, cy, r, env)
    for p in front:
        if abs(orbit * math.sin(math.radians(p[1]))) > r + 15:   # in front of the ball it would hide it
            panel(*p)
    cv.mark('ball', *box)


TECHNIQUE = Technique(
    id='chrome-reflection',
    name='Chrome reflection',
    family='camera',
    group='Lighting & surface',
    aliases=('environment reflection', 'mirror finish', 'environment map', 'reflection mapping'),
    definition='A mirror-polished object shows the scene around it painted onto its surface, bent by its '
               'shape, so things around it curve and squeeze toward its edges as they move.',
    phrasings=('make the ball look like polished chrome reflecting the room',
               'a shiny metal sphere where you can see the coloured lights wrap around it',
               'give the object a mirror finish so the surroundings show up in it'),
    related=('chrome-specular-shimmer', 'y2k-chrome', 'text-reflection-shimmer', 'gooch-shading',
             'fresnel-edge-glow', 'low-poly-faceting'),
    api=('videobuilder.techniques.camera.chrome_reflection.draw_chrome_ball',
         'videobuilder.techniques.camera.chrome_reflection.reflect_sphere',
         'videobuilder.techniques.camera.chrome_reflection.environment'),
    demo=lambda: demo.film(draw),
)

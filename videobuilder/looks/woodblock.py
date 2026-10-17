"""Ukiyo-e woodblock: flat fills with thick ink outlines on a paper ground,
a graded sky and a red sun. A great wave rises out of the open water and
curls over a hollow once per shot (on `age`), its foam claws flicking; cloud
strips slide, the water's lines roll, and slanting rain falls."""
import math
import random

import cairo

from . import kit
from .look import Look
from .. import paths
from ..ease import clamp01

INK = '#1c1a22'
PRUSSIAN = '#1d3a63'
PAPER = '#efe2c4'
FOAM = '#f6f3ea'
# role -> the fills its regions take in turn
FILLS = {
    'land': ('#4a5a3a', '#5c6a44'),
    'building': ('#f3ece0', '#c8402f', '#d8c8a8'),
    'figure': ('#8a5a3a', PAPER),
    'light': ('#f2c34a',),
    'sky': ('#e7b8a8',),
    'water': ('#24508a',),
}


def _wave(p):
    """The big wave at phase p (0..1), drawn in its own 1080-wide frame
    (open water from x=560 to 1100, horizon at y=1130): the body outline,
    the hollow (centre, radius) and the lip's arc."""
    e = 0.5 - 0.5 * math.cos(math.pi * p)
    R = 120 + 70 * e
    cx, cy = 900 - 90 * e, 1240 - 260 * e          # the crest
    ox, oy = cx - 0.35 * R, cy + R                  # the curl's centre
    body = [(560, 1700)]
    for i in range(1, 9):                           # the face, rising to under the curl
        s = i / 8
        body.append((560 + (ox - 0.9 * R - 560) * s, 1700 - (1700 - (oy + 0.6 * R)) * s ** 1.3))
    body += [(ox - 0.9 * R, oy + 0.4 * R), (ox - R, oy), (ox - 0.7 * R, oy - 0.7 * R), (ox, oy - R), (cx, cy),
             (cx + 0.6 * R, cy + 0.2 * R), (1010, 1240 - 80 * e), (1100, 1280), (1100, 1760), (560, 1760)]
    lip = [(ox + R * math.cos(a), oy + R * math.sin(a))
           for a in (-math.pi / 2 - k / 14 * (0.9 + 0.35 * e) * math.pi for k in range(15))]
    return body, (ox, oy, 0.5 * R), lip


def _draw_wave(cv, scene, t, age):
    water = scene.open_water()
    if not water:
        return
    x0, x1 = water
    s = min((x1 - x0) / 540, (scene.h - scene.horizon) / 650)
    if s <= 0.05:
        return
    sx = min((x1 - x0) * 0.8 / 540, 1.6 * s) if (x1 - x0) / 540 > s else s   # wider on a wide frame
    # the wave hugs the far side of the open water and curls back towards the land
    land_left = (x0 + x1) / 2 >= scene.w / 2
    c = cv.ctx
    c.save()
    if land_left:
        c.translate(x1 - 1100 * sx, scene.horizon - 1130 * s)
        c.scale(sx, s)
    else:
        c.translate(x0 + 1100 * sx, scene.horizon - 1130 * s)
        c.scale(-sx, s)
    p = clamp01(age / 3.0)          # rises and curls once per shot
    body, (hx, hy, hr), lip = _wave(p)
    kit.fill(cv, body, '#24508a', outline=INK, width=5)
    for k in range(1, 5):                     # bands along the back of the wave
        band = [(x + 6 * k, y + 34 * k) for x, y in body[-8:-4]]
        paths.draw(cv, band, '#e9eef0', width=4, alpha=0.75)
    kit.fill(cv, kit.circle_pts(hx, hy, hr * (1.1 + 0.3 * p), 40), PAPER, outline=INK, width=4)   # the hollow
    paths.draw(cv, lip, INK, width=40)
    paths.draw(cv, lip, FOAM, width=32)
    for i, (x, y) in enumerate(lip[1:]):          # the foam's claws, flicking outward
        a = math.atan2(y - hy, x - hx) + 0.35 * math.sin(t * 7 + i)
        tip = (x + 40 * math.cos(a), y + 40 * math.sin(a))
        kit.fill(cv, [(x - 9 * math.sin(a), y + 9 * math.cos(a)), tip, (x + 9 * math.sin(a), y - 9 * math.cos(a))],
                 FOAM, outline=INK, width=2)
    rs = random.Random(int(t * 10))
    for _ in range(18):                      # spray, re-thrown ten times a second
        kit.disc(cv, lip[0][0] + rs.uniform(-80, 120), lip[0][1] + rs.uniform(-120, 40), rs.uniform(3, 7), FOAM)
    c.restore()


def paint(cv, scene, t, age):
    c = cv.ctx
    u = scene.u
    w, h = scene.w, scene.h
    sky_h = scene.sky_bottom
    cv.rect(0, 0, w, h, PAPER)
    g = cairo.LinearGradient(0, 0, 0, sky_h * 0.67)
    g.add_color_stop_rgba(0, *kit.rgb(PRUSSIAN))
    g.add_color_stop_rgba(1, *kit.rgb(PRUSSIAN, 0))
    c.rectangle(0, 0, w, sky_h * 0.67)
    c.set_source(g)
    c.fill()
    for i, (fy, fw, speed) in enumerate(((0.38, 380, 30), (0.5, 420, 18), (0.6, 300, -26), (0.67, 520, -14),
                                         (0.8, 360, 24), (0.9, 280, -32))):
        bw = fw * u
        x = (140 * u + i * 330 * u + speed * u * t) % (w + bw) - bw
        y = fy * sky_h
        cv.rect(x, y, bw, 26 * u, '#e7b8a8', radius=13 * u)
        cv.rect(x + 60 * u, y + 34 * u, bw * 0.6, 18 * u, '#e7b8a8', radius=9 * u)
    if scene.sun:
        kit.disc(cv, scene.sun[0], scene.sun[1], scene.sun[2], '#c8402f')
    if scene.horizon is not None:
        top = scene.horizon
        cv.rect(0, top, w, h - top, PRUSSIAN)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        rows = max(3, int((h - top) / (70 * u)))
        for row in range(rows):
            y = top + 40 * u + row * 70 * u
            c.new_path()
            x = 0.0
            while x <= w + 26 * u:
                c.line_to(x, y + 14 * u * math.sin(x / (40 * u) + row * 1.3 + t * 2.4))
                x += 26 * u
            c.set_source_rgba(*kit.rgb('#e9eef0', 0.85))
            c.set_line_width(4 * u)
            c.stroke()
        _draw_wave(cv, scene, t, age)
    turn = kit.Turns(FILLS, {'building': INK}, thin=30 * u)
    lit = 0.6 + 0.4 * abs(math.sin(t * math.pi / 2))
    for region in scene.regions:
        kit.fill(cv, region.points, turn(region), alpha=lit if region.role == 'light' else 1.0,
                 outline=INK, width=5 * u)
    for i in range(60):                      # slanting woodblock rain, falling
        x0 = (i * 97 * u) % (w + 400 * u) - 200 * u
        y = ((i * 53 * u) % h + 900 * u * t) % (h + 200 * u) - 200 * u
        cv.line(x0 + y * 0.18, y, x0 + (y + 70 * u) * 0.18, y + 70 * u, INK, width=2 * u)


LOOK = Look('woodblock', 'Ukiyo-e woodblock', 'a great wave curls over', paint,
            aliases=('ukiyo-e', 'ukiyoe', 'japanese print', 'woodcut', 'woodblock print', 'great wave'))

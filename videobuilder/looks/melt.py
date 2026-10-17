"""Surrealist melt: smooth gradients and soft shapes in a dream light.
Buildings and figures sway and sag like warm wax, the sun sags and drips
into a mirror sea, stones float across the sky, and a clock draped over the
edge of the land melts, dripping from its lowest point."""
import math

import cairo

from . import kit
from .look import Look
from .. import paths

WAX = {'building': ('#ede3d2', '#c9b8a0', '#e0c8a8'), 'figure': ('#5a3a2a', '#f6ead2'), 'light': ('#f2c870',)}
LAND = '#b98a5a'


def _clock(cv, scene, t):
    """The clock draped over the land's ledge (or in the open sky, with no
    land): its right side sags down and in, pulsing slowly, and a drip forms
    at its lowest point and lets go."""
    u = scene.u
    ledge = scene.ledge()
    if ledge:
        sign = 1 if ledge[0] < scene.w / 2 else -1    # it melts out over the open side
        cx, cy = ledge[0] - sign * 70 * u, ledge[1] + 30 * u
    else:
        cx, cy, sign = scene.w * 0.3, scene.sky_bottom * 0.7, 1
    r = 140 * u
    edge = cx + sign * r * 0.2
    droop = 0.35 + 0.65 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 2.0))

    def melt(x, y):
        d = (x - edge) * sign
        if d <= 0:
            return x, y
        return edge + sign * (d * (1 - 0.45 * droop) + 6 * u * droop), y + droop * 0.075 * u * (d / u) ** 1.55

    face = [melt(x, y) for x, y in kit.circle_pts(cx, cy, r, 96, sy=0.42)]
    rim = [melt(x, y + 14 * u) for x, y in kit.circle_pts(cx, cy, r, 96, sy=0.42)]
    kit.fill(cv, rim, '#a8782a')
    kit.fill(cv, face, '#f4ecd8', outline='#c8963a', width=6 * u)
    for i in range(12):
        a = 2 * math.pi * i / 12
        a0 = melt(cx + 0.8 * r * math.cos(a), cy + 0.8 * 0.42 * r * math.sin(a))
        a1 = melt(cx + 0.92 * r * math.cos(a), cy + 0.92 * 0.42 * r * math.sin(a))
        cv.line(*a0, *a1, '#3a2a1a', width=4 * u)
    for length, speed, width in ((0.55, 0.5, 7), (0.85, 3.0, 4)):
        a = speed * t - math.pi / 2
        hand = [melt(cx + s * length * r * math.cos(a), cy + s * length * 0.42 * r * math.sin(a))
                for s in (0, 0.25, 0.5, 0.75, 1)]
        paths.draw(cv, hand, '#3a2a1a', width=width * u)
    tip = max(face, key=lambda p: p[1])
    q = (t / 1.2) % 1.0
    stretch = min(q / 0.6, 1)
    fall = max(0, (q - 0.6) / 0.4)
    dy = tip[1] + 12 * u + 50 * u * stretch + 420 * u * fall * fall
    if fall == 0:
        kit.fill(cv, [tip, (tip[0] - 9 * u, tip[1] + 8 * u), (tip[0], dy), (tip[0] + 9 * u, tip[1] + 8 * u)], '#f4ecd8')
    kit.fill(cv, kit.circle_pts(tip[0], dy, 11 * u, 24, sy=1.3), '#f4ecd8', outline='#c8963a', width=3 * u)


def paint(cv, scene, t, age):
    c = cv.ctx
    u = scene.u
    w, h = scene.w, scene.h
    sky_h = scene.sky_bottom
    g = cairo.LinearGradient(0, 0, 0, sky_h)
    for s, col in ((0, '#1f4a5a'), (0.55, '#6a8f8a'), (1, '#f2b880')):
        g.add_color_stop_rgba(s, *kit.rgb(col))
    c.rectangle(0, 0, w, sky_h)
    c.set_source(g)
    c.fill()
    if scene.horizon is not None:
        g = cairo.LinearGradient(0, scene.horizon, 0, h)
        g.add_color_stop_rgba(0, *kit.rgb('#d9a070'))
        g.add_color_stop_rgba(1, *kit.rgb('#5a3a2a'))
        c.rectangle(0, scene.horizon, w, h - scene.horizon)
        c.set_source(g)
        c.fill()
    sag = 0.5 + 0.5 * math.sin(2 * math.pi * t / 1.8)
    if scene.sun:                                  # the sun sags, and drips towards the sea
        mx, my, mr = scene.sun
        mx += 18 * u * math.sin(2 * math.pi * t / 3.6)
        sun = [(x, y + (max(0, y - my) / u) ** 1.4 * u * 0.06 * (0.5 + sag)) for x, y in kit.circle_pts(mx, my, mr)]
        kit.fill(cv, sun, '#f6ead2')
        bottom = max(y for _, y in sun)
        for k in range(2):
            q = ((t + k * 0.75) / 1.5) % 1.0
            dy = bottom + (sky_h + 60 * u - bottom) * q * q
            kit.fill(cv, kit.circle_pts(mx - 12 * u + k * 26 * u, dy, 14 * u * (1 - 0.4 * q), 24, sy=1.4), '#f6ead2')
        if scene.horizon is not None:              # its reflection, stretched long
            kit.fill(cv, kit.circle_pts(mx, scene.horizon + 140 * u, mr * 0.9, 48, sy=1.6), '#f6ead2', 0.18)
    if scene.horizon is not None:
        for row in range(16):                     # ripples sliding across the mirror sea
            y = scene.horizon + (24 + row * row * 3.2) * u
            if y > h:
                break
            rw = (120 + row * 22) * u
            for k in range(5):
                x = (k * 260 * u + row * 137 * u + (40 + row * 6) * u * t) % (w + rw) - rw
                cv.rect(x, y, rw, (3 + row * 0.5) * u, '#f6e0c0', alpha=0.55)
    for i, (fx, fy, r, speed) in enumerate(((0.11, 0.46, 46, 34), (0.57, 0.8, 30, -26), (0.9, 0.4, 38, 22),
                                           (0.39, 0.69, 26, 40), (0.7, 0.88, 22, -30))):
        r *= u                                     # stones that float, as in a dream
        x = (fx * w + speed * u * t) % (w + 200 * u) - 100 * u
        y = fy * sky_h + 16 * u * math.sin(t * 1.4 + i)
        kit.fill(cv, kit.circle_pts(x, y, r, 32, sy=0.8), '#8a6a5a')
        kit.fill(cv, kit.circle_pts(x - r * 0.25, y - r * 0.2, r * 0.55, 24, sy=0.6), '#b8968a')
    # parts of one structure sway together: each group's wax is measured on the group's own extent
    groups = {}
    for region in scene.regions:
        if region.role not in ('land', 'sky', 'water'):
            group = 'figure' if region.role == 'figure' else 'building'
            x0, y0, rw, rh = region.bbox
            top, bottom = groups.get(group, (y0, y0 + rh))
            groups[group] = (min(top, y0), max(bottom, y0 + rh))
    turn = kit.Turns(WAX, {'building': '#4a3a3a'}, thin=30 * u)
    for region in scene.regions:
        if region.role in ('land', 'sky', 'water'):
            colour = {'land': LAND, 'sky': '#6a8f8a', 'water': '#d9a070'}[region.role]
            kit.fill(cv, region.points, colour)
            if region.role == 'land':           # a long shadow across its top
                x0, y0, rw, rh = region.bbox
                with kit.clip_to(cv, region.points):
                    kit.fill(cv, [(x0, y0), (x0 + rw * 0.6, y0), (x0 + rw * 0.2, y0 + rh * 0.12), (x0, y0 + rh * 0.12)],
                             '#6a4a3a', 0.35)
            continue
        top, bottom = groups['figure' if region.role == 'figure' else 'building']
        tall = max(bottom - top, 60 * u)

        def wax(x, y, bottom=bottom, tall=tall):   # sways and sags like soft wax, more towards the top
            up = (bottom - y) / tall
            return (x + 26 * u * up * up * math.sin(2 * math.pi * t / 2.4),
                    y + 30 * u * up * up * sag * (tall / (430 * u)) ** 0.5)
        kit.fill(cv, kit.warp(region.points, wax), turn(region))
    _clock(cv, scene, t)


LOOK = Look('melt', 'Surrealist melt', 'the clock melts, the tower sways', paint,
            aliases=('surreal', 'surrealist', 'surrealism', 'melting', 'dreamlike', 'dream'))

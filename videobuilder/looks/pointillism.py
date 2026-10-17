"""Pointillism: a jittered grid of dots, each coloured by the role of the
shape it falls in. Every dot shimmers towards a neighbouring tone, light
bands roll through the water, buildings are banded, and the beacon's beams
brighten the dots they sweep across."""
import math

from . import kit
from .look import Look

PAPER = '#f4ecdc'
SKY = ('#9fc8e8', '#f6d7b8')     # graded top to horizon
PALETTE = {
    'sky': None,
    'sun': ('#fff6c8', '#ffd98a', '#ffe9a8'),
    'land': ('#5c8a3a', '#8aa84a', '#c7a35a', '#3d6a4a'),
    'building': ('#6a5a7a', '#7a6a8a', '#5a5070'),
    'figure': ('#6a3a2a', '#fbe8d0', '#8a4a3a'),
    'light': ('#e05a3a', '#f08a4a', '#ffd06a'),
    'water': ('#2f8ab0', '#4fb0c8', '#1f6a9a', '#8ad0d8'),
}
BAND = ('#d0443a', '#e8703a')


def paint(cv, scene, t, age):
    c = cv.ctx
    u = scene.u
    cv.rect(0, 0, scene.w, scene.h, PAPER)
    beam_polys = kit.beams(scene, t)
    sun = scene.sun
    top = scene.sky_bottom * 0.35
    building_band = 74 * u
    r_dot = 6.5 * u
    for x, y, tone, ph, sp in kit.jittered_grid(scene.w, scene.h, 14 * u, 5 * u, 5):
        shimmer = 0.5 + 0.5 * math.sin(sp * t + ph)
        role = scene.role_at(x, y)
        if role == 'sky' and sun and math.hypot(x - sun[0], y - sun[1]) < sun[2]:
            role = 'sun'
        if role == 'sky':
            base = kit.mix(*SKY, max(0.0, min(1.0, (y - top) / max(1.0, scene.sky_bottom - top))))
            alt = kit.rgb('#c9a8e0' if tone < 0.5 else '#ffffff')
            col = tuple(base[i] + (alt[i] - base[i]) * 0.45 * shimmer for i in range(3))
        elif role == 'building' and int(y / building_band) % 2 == 1:
            col = kit.rgb(BAND[tone < 0.5])[:3]
        else:
            pal = PALETTE[role]
            col = kit.rgb(pal[int((tone + 0.25 * shimmer) * len(pal)) % len(pal)])[:3]
            if role == 'water' and math.sin(y / (16 * u) + x / (55 * u) - t * 3.2) > 0.72:
                col = kit.rgb('#e8f6f2')[:3]
        if role in ('sky', 'water', 'sun'):
            for pts, s in beam_polys:
                if abs(y - scene.beacon[1]) < 140 * u and kit.inside(pts, x, y):
                    col = tuple(col[i] + (1 - col[i]) * 0.5 * s for i in range(3))
        c.new_path()
        c.arc(x, y, r_dot, 0, 2 * math.pi)
        c.set_source_rgb(*col)
        c.fill()


LOOK = Look('pointillism', 'Pointillism', 'ten thousand dots that shimmer', paint,
            aliases=('points', 'dots', 'dotted', 'stippled', 'neo-impressionist'))

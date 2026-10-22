"""Hyperlapse: the camera travels steadily through a place while time runs
hundreds or thousands of times too fast -- the sky goes from dawn to night,
clouds race, crowds flicker in and out and traffic smears into light trails,
all while the move itself stays smooth. videobuilder had no helper that
splits a scene's clock from its camera, so this module adds one."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ... import paths


def hyperlapse(cv, scene, t, speed, pace, start=0.0, shutter=0.5, fps=30):
    """Draw `scene(cv, clock, cam, exposure)` as a hyperlapse at film time `t`
    (seconds). The scene's own clock runs `speed` times real time from
    `start` (scene seconds), while the camera advances a steady `pace` units
    per film second, so the move stays smooth however fast time goes.
    `exposure` is how much scene time one frame's shutter spans (`shutter`
    is the fraction of a frame it stays open): anything that moves faster
    than that should be drawn as a streak covering it. Returns the clock."""
    clock = start + t * speed
    scene(cv, clock, t * pace, speed * shutter / fps)
    return clock


# ---- the demo: a walk down a city street from dawn to night, in 3 seconds ----

W, H = demo.W, demo.H
HORIZON, F, EYE = H * 0.44, W * 0.5, 1.6  # horizon y, focal length (px), camera height (m)
START, END = 6 * 3600, 22 * 3600  # 06:00 to 22:00 in scene seconds
SPEED = (END - START) / demo.SECONDS
PACE = 16.0  # metres per film second
NEAR, FAR = 0.8, 170.0
ROAD, WALK, FACADE = 5.0, 7.5, 12.5  # half-widths (m): road, sidewalk edge, building line
SKY = ((5.0, '#1c2444'), (6.6, '#e7a06c'), (8.5, '#86b6db'), (16.5, '#8ab4d6'), (18.6, '#e0775a'),
       (20.0, '#2a2b52'), (22.0, '#111530'))


def _blocks(side, seed):
    rnd = random.Random(seed)
    out, z = [], -4.0
    while z < FAR + PACE * demo.SECONDS + 20:
        n = rnd.uniform(9, 22)
        tone = rnd.choice(('#8d8478', '#a59a8c', '#6f747c', '#9a8b7e', '#7e8a8f'))
        lit = [[rnd.random() for _ in range(int(n / 3))] for _ in range(8)]
        out.append((side, z, z + n, rnd.uniform(9, 24), tone, lit))
        z += n
    return out


BLOCKS = _blocks(-1, 4) + _blocks(1, 9)


def _mix_stops(stops, x):
    if x <= stops[0][0]:
        return stops[0][1]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if x <= b:
            return demo.kit.mix(ca, cb, (x - a) / (b - a))
    return stops[-1][1]


def _night(hour):
    """0 in full daylight, 1 at night."""
    return max(vb.clamp01((7.2 - hour) / 1.2), vb.clamp01((hour - 18.3) / 1.8))


def _pt(x, y, dz):
    return W / 2 + F * x / dz, HORIZON + F * (EYE - y) / dz


def _quad_x(cv, x, z0, z1, y0, y1, cam, color, alpha=1.0):
    """A wall in the plane at side offset `x`, between depths z0..z1, heights y0..y1."""
    d0, d1 = max(z0 - cam, NEAR), min(z1 - cam, FAR)
    if d1 <= d0:
        return
    paths.draw(cv, [_pt(x, y0, d0), _pt(x, y0, d1), _pt(x, y1, d1), _pt(x, y1, d0)], color, fill=True,
               alpha=alpha)


def _quad_y(cv, x0, x1, z0, z1, cam, color, alpha=1.0):
    """A patch of ground (y = 0) between side offsets x0..x1 and depths z0..z1."""
    d0, d1 = max(z0 - cam, NEAR), min(z1 - cam, FAR)
    if d1 <= d0:
        return
    paths.draw(cv, [_pt(x0, 0, d0), _pt(x1, 0, d0), _pt(x1, 0, d1), _pt(x0, 0, d1)], color, fill=True,
               alpha=alpha)


def _sky(cv, hour, clock):
    cv.fill(_mix_stops(SKY, hour))
    night = _night(hour)
    rnd = random.Random(3)
    for _ in range(40):  # stars come out
        sx, sy = rnd.uniform(0, W), rnd.uniform(0, HORIZON)
        demo.dot(cv, sx, sy, rnd.uniform(0.8, 1.8), color=demo.INK, alpha=0.8 * vb.clamp01(night * 1.5 - 0.5))
    u = (hour - 6.4) / 12.8  # the sun arcs over the gap between the rooftops
    if 0 < u < 1:
        sx, sy = W * (0.3 + 0.4 * u), HORIZON - 30 - 210 * math.sin(math.pi * u)
        warm = 1 - math.sin(math.pi * u)
        demo.dot(cv, sx, sy, 44, color=demo.kit.mix('#fff6d8', '#ffb070', warm), alpha=0.25)
        demo.dot(cv, sx, sy, 24, color=demo.kit.mix('#fffbe8', '#ffc48a', warm))
    rnd = random.Random(5)
    for _ in range(9):  # clouds race across
        y, v, size = rnd.uniform(30, HORIZON - 60), rnd.uniform(0.010, 0.020), rnd.uniform(40, 90)
        x = (rnd.uniform(0, W + 400) + clock * v) % (W + 400) - 200
        tone = demo.kit.mix('#ffffff', '#3a3d5c', night)
        for k in range(4):
            demo.dot(cv, x + (k - 1.5) * size * 0.55, y + (k % 2) * size * 0.12, size * (0.42 + 0.1 * (k % 2)),
                     color=tone, alpha=0.55)


def _street(cv, clock, cam, exposure):
    hour = clock / 3600
    night = _night(hour)
    frame = int(clock // max(exposure, 1e-6))  # a fresh moment every frame: people come and go
    _sky(cv, hour, clock)
    cv.rect(0, HORIZON, W, H - HORIZON, '#4a4c52')
    for s in (-1, 1):
        _quad_y(cv, s * ROAD, s * WALK, cam, cam + FAR, cam, '#8a867e')
    for k in range(int(cam // 8), int((cam + FAR) // 8) + 1):  # centre dashes
        _quad_y(cv, -0.12, 0.12, k * 8, k * 8 + 3.5, cam, '#e8e2cf', alpha=0.85)
    lit = []
    for side, z0, z1, h, tone, panes in sorted(BLOCKS, key=lambda b: -b[1]):
        if z1 < cam + NEAR or z0 > cam + FAR:
            continue
        x = side * FACADE
        _quad_x(cv, x, z0, z1, 0, h, cam, tone)
        _quad_x(cv, x, z0, z0 + 0.4, 0, h, cam, '#000000', alpha=0.18)  # seam between buildings
        for row, cells in enumerate(panes):
            y = 3.5 + row * 3.2
            if y + 1.6 > h:
                break
            for col, r in enumerate(cells):
                wz = z0 + 1.2 + col * 3
                if wz + 1.4 > z1:
                    break
                on = r < night * 0.85 - 0.05 * row  # windows light up as night falls
                _quad_x(cv, x, wz, wz + 1.4, y, y + 1.6, cam, '#2b3240', alpha=0.55)
                if on:
                    lit.append((x, wz, y))
    rnd = random.Random(frame)  # pedestrians: a different crowd in every frame, thinning out at night
    busy = 0.25 + 0.75 * math.sin(math.pi * vb.clamp01((hour - 6.5) / 13))
    for _ in range(int(40 * busy)):
        side, z = rnd.choice((-1, 1)), cam + rnd.uniform(3, 70)
        px = side * rnd.uniform(WALK + 0.4, FACADE - 0.6)
        x0, y0 = _pt(px - 0.25, 1.75, z - cam)
        x1, y1 = _pt(px + 0.25, 0, z - cam)
        cv.rect(x0, y0, x1 - x0, y1 - y0, rnd.choice(('#2e3440', '#7a3b34', '#38506b', '#5b5348')),
                radius=(x1 - x0) / 2, alpha=0.5)
    cv.fill('#0a0d1f', alpha=0.62 * night)  # dusk falls over everything that isn't a light
    for x, wz, y in lit:
        _quad_x(cv, x, wz, wz + 1.4, y, y + 1.6, cam, '#ffd27a', alpha=0.9)
    for k in range(int(cam // 14), int((cam + FAR) // 14) + 1):  # street lamps
        for s in (-1, 1):
            dz = k * 14 - cam
            if dz < NEAR + 0.4:
                continue
            bx, by = _pt(s * (ROAD + 0.6), 0, dz)
            tx, ty = _pt(s * (ROAD + 0.6), 6, dz)
            hx, hy = _pt(s * (ROAD - 0.6), 6, dz)
            cv.line(bx, by, tx, ty, '#2c2e33', width=max(1.0, 9 / dz))
            cv.line(tx, ty, hx, hy, '#2c2e33', width=max(1.0, 7 / dz))
            glow = vb.clamp01((night - 0.3) / 0.4)
            if glow:
                demo.dot(cv, hx, hy, 260 / dz, color='#ffcf80', alpha=0.25 * glow)
                demo.dot(cv, hx, hy, 70 / dz, color='#fff3d0', alpha=glow)
    trails = 0.15 + 0.85 * night  # traffic, smeared by the long exposure into rivers of light
    for lane, color in ((-2.4, '#fff4e0'), (-1.2, '#fff4e0'), (1.2, '#ff3b30'), (2.4, '#ff3b30')):
        for j in range(3):
            off = lane + rnd.uniform(-0.35, 0.35)
            a, b = _pt(off, 0.7, NEAR + 0.6), _pt(off, 0.7, FAR)
            cv.line(*a, *b, color if night > 0.3 else '#d8d4cc', width=rnd.uniform(2, 5),
                    alpha=trails * rnd.uniform(0.35, 0.8))
    _clock(cv, hour)


def _clock(cv, hour):
    hh, mm = int(hour) % 24, int(hour * 60) % 60
    cv.rect(28, 24, 168, 54, '#000000', radius=12, alpha=0.45)
    demo.word(cv, f'{hh:02d}:{mm:02d}', 112, 51, size=34, color=demo.INK, font=demo.mono(34, 700))
    demo.word(cv, f'x{SPEED:,.0f}', W - 100, 51, size=20, color=demo.INK, font=demo.mono(20), alpha=0.75)


def draw(n, cv):
    hyperlapse(cv, _street, n / demo.FPS, SPEED, PACE, start=START, fps=demo.FPS)


TECHNIQUE = Technique(
    id='hyperlapse',
    name='Hyperlapse',
    family='camera',
    group='Camera moves',
    aliases=('moving time-lapse', 'motion time-lapse', 'walking time-lapse'),
    definition='The camera glides smoothly through a place while time races by around it, so hours of '
               'light, weather, crowds and traffic pass in the few seconds the move takes.',
    phrasings=('a time-lapse where the camera keeps moving down the street',
               'fly through the city while the day goes by in seconds',
               'sped-up footage with a smooth travelling shot, clouds and cars blurring past'),
    related=('time-remapping', 'timeline-scroll', 'accumulation-motion-blur', 'scatter-time-playback',
             'multiples', 'seamless-loop'),
    api=('videobuilder.techniques.camera.hyperlapse.hyperlapse',),
    demo=lambda: demo.film(draw),
)

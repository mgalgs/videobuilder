"""Tilt-shift miniature: a level band across the picture stays crisp while
the picture above and below it goes steadily softer, the shallow focus of a
macro lens, so an ordinary wide scene looks like a tabletop model."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type.kit import blurred


def _soft(cv, draw, radius):
    """`draw(cv)` blurred by `radius` over the whole frame. An enlarged copy
    goes underneath so the frame's edges blur into picture, not into empty
    space."""
    box = vb.Box.of(cv)
    grow = 1 + 5 * radius / min(box.w, box.h)

    def paint(c):
        with c.layer(dx=box.cx * (1 - grow), dy=box.cy * (1 - grow), scale=grow):
            draw(c)
        with c.clip(box.x, box.y, box.w, box.h):
            draw(c)
    with cv.clip(box.x, box.y, box.w, box.h):
        blurred(cv, box, radius, paint)


def tilt_shift(cv, draw, focus=None, band=0.16, falloff=0.32, blur=14, levels=6):
    """Draw `draw(cv)` with a tilt-shift focus band: sharp within `band` (a
    fraction of the frame's height) either side of the line y = `focus`
    (default the frame's middle), then blurring smoothly up to `blur` px
    over the next `falloff` of the height, above and below alike.

    The falloff is built from `levels` blurred copies, each faded in by a
    gradient over its own slice of the falloff, so there is no visible step.
    Animate `blur` from 0 to bring the miniature look in, or `focus` to rack
    the band up or down the frame."""
    draw(cv)
    if blur * cv.scale_factor() < 0.5:
        return
    h = cv.height
    cy = h / 2 if focus is None else focus
    half, ramp = band * h, falloff * h
    ctx = cv.ctx
    for i in range(1, levels + 1):
        near, far = half + ramp * (i - 1) / levels, half + ramp * i / levels
        mask = cairo.LinearGradient(0, cy - far, 0, cy + far)
        for y, a in ((cy - far, 1), (cy - near, 0), (cy + near, 0), (cy + far, 1)):
            mask.add_color_stop_rgba((y - (cy - far)) / (2 * far), 0, 0, 0, a)
        ctx.push_group()
        _soft(cv, draw, blur * i / levels)
        ctx.pop_group_to_source()
        ctx.mask(mask)


# The demo: a little town seen from up high, the road through the middle in
# focus, cars driving along it; the focus band closes in and it turns to a toy.

SKY, FIELD, FIELD2 = '#2b3550', '#3f6b4a', '#355c40'
ROAD_Y = demo.H * 0.56
HOUSES = ('#e8d6b0', '#d98c6a', '#f0eee6', '#c7d6e8', '#e6b85c')


def _house(cv, x, base, s, color):
    w, h = 46 * s, 30 * s
    cv.rect(x - w / 2, base - h, w, h, color, radius=2 * s)
    c = cv.ctx
    c.move_to(x - w / 2 - 5 * s, base - h)
    c.line_to(x, base - h - 22 * s)
    c.line_to(x + w / 2 + 5 * s, base - h)
    c.close_path()
    c.set_source_rgba(*vb.rgba('#9b3d34'))
    c.fill()
    cv.rect(x - 6 * s, base - 16 * s, 12 * s, 16 * s, '#4a3a30')


def _tree(cv, x, base, s):
    cv.rect(x - 3 * s, base - 14 * s, 6 * s, 14 * s, '#5a4030')
    demo.dot(cv, x, base - 26 * s, 17 * s, color='#2f7a4a')


def _car(cv, x, y, color, s=1.0):
    cv.rect(x - 26 * s, y - 13 * s, 52 * s, 22 * s, color, radius=6 * s)
    cv.rect(x - 14 * s, y - 22 * s, 28 * s, 12 * s, color, radius=4 * s)
    cv.rect(x - 11 * s, y - 20 * s, 22 * s, 8 * s, '#bfe3f2', radius=2 * s)
    for dx in (-15, 15):
        demo.dot(cv, x + dx * s, y + 9 * s, 6 * s, color='#1b1b1f')


def town(cv, t):
    """The demo's subject at `t` seconds: sky, hills, rows of houses and
    trees stepping back in depth, and a road with cars on it."""
    W, H = demo.W, demo.H
    cv.fill(SKY)
    demo.dot(cv, W * 0.8, H * 0.13, 34, color='#f2d36b')
    for cx, r, col in ((W * 0.2, 420, '#2f4f45'), (W * 0.75, 480, '#294438')):
        demo.dot(cv, cx, H * 0.36 + r, r, color=col)
    cv.rect(0, H * 0.3, W, H * 0.7, FIELD)
    for row, (base, s, n) in enumerate(((H * 0.33, 0.55, 14), (H * 0.42, 0.75, 10), (H * 0.51, 0.95, 8))):
        for k in range(n):
            x = (k + 0.5 + 0.35 * (row % 2)) * W / n
            if (k + row) % 3 == 0:
                _tree(cv, x, base, s)
            else:
                _house(cv, x, base, s, HOUSES[(k * 3 + row) % len(HOUSES)])
    cv.rect(0, ROAD_Y - 22, W, 58, '#55565c')
    for k in range(16):
        cv.rect(k * W / 15 - 40, ROAD_Y + 6, 34, 4, '#e9e6df')
    for x0, v, col, lane in ((-60, 230, demo.ACCENT, -4), (W * 0.45, 190, demo.TEAL, -4),
                             (W + 60, -210, '#f2d36b', 24)):
        x = (x0 + v * t) % (W + 160) - 80
        _car(cv, x, ROAD_Y + lane, col, 0.8)
    cv.rect(0, H * 0.66, W, H * 0.34, FIELD2)
    for row, (base, s, n) in enumerate(((H * 0.8, 1.3, 6), (H * 1.0, 1.8, 5))):
        for k in range(n):
            x = (k + 0.3 + 0.4 * row) * W / n
            if (k + row) % 2:
                _tree(cv, x, base, s)
            else:
                _house(cv, x, base, s, HOUSES[(k + 2 * row) % len(HOUSES)])


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 1.4))
    tilt_shift(cv, lambda c: town(c, n / demo.FPS), focus=ROAD_Y, band=0.06, falloff=0.24, blur=22 * p)
    cv.mark('focus band', 0, ROAD_Y - 0.06 * demo.H, demo.W, 0.12 * demo.H)


CAPABILITY = Capability(
    id='tilt-shift-miniature',
    name='Tilt-shift miniature',
    family='camera',
    group='Depth',
    aliases=('tilt-shift', 'miniature effect', 'fake miniature', 'selective focus band'),
    definition='Only a thin level strip of the picture is in focus and everything above and below it '
               'melts into blur, so a real wide view looks like a tiny model town.',
    phrasings=('make the city look like a toy model',
               'blur the top and bottom of the shot and keep a sharp stripe in the middle',
               'that miniature look where real streets seem tiny'),
    related=('zoom-blur', 'tilt', 'focus-breathing', 'whip-pan', 'dolly-zoom', 'handheld-shake'),
    api=('videobuilder.capabilities.camera.tilt_shift_miniature.tilt_shift', 'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(draw),
)

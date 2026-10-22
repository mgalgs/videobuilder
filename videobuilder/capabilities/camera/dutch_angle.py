"""Dutch angle: the camera rolls about its lens axis, so the horizon and the
verticals in the shot run on a slant instead of level and plumb."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def cover_scale(width, height, angle):
    """How much a `width` x `height` picture rotated by `angle` radians must
    grow to still cover the whole frame, with no empty corners."""
    a = abs(angle) % math.pi
    a = min(a, math.pi - a)
    return math.cos(a) + max(width / height, height / width) * math.sin(a)


def dutch_angle(cv, scene, angle, cx=None, cy=None, cover=True, color=demo.BG):
    """Draw `scene(cv)` as seen by a camera rolled `angle` radians (positive
    turns the picture clockwise) about (`cx`, `cy`), the frame centre by
    default. With `cover`, the picture grows just enough that the tilted
    shot still fills the frame; otherwise `color` shows in the corners.

    In a film, wrap the shot: `dutch_angle(cv, lambda c: shot(c, n), math.radians(12) * vb.ease_in_out_quart(p))`."""
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    s = cover_scale(w, h, angle) if cover else 1.0
    if not cover:
        cv.fill(color)
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(angle)
    c.scale(s, s)
    c.translate(-cx, -cy)
    with cv.clip(0, 0, w, h):
        scene(cv)
    c.restore()


# ---- demo ----

HORIZON = demo.H * 0.62
TILT = math.radians(12)


def _street(cv):
    """A plain scene full of level lines and plumb lines: a skyline of
    windowed blocks on a horizon, a ground grid, and a dot on the ground."""
    W, H = demo.W, demo.H
    cv.fill(demo.BG)
    blocks = ((40, 130, 170), (190, 100, 230), (310, 150, 130), (480, 110, 210),
              (610, 140, 150), (770, 110, 190))
    for i, (x, bw, bh) in enumerate(blocks):
        top = HORIZON - bh
        cv.rect(x, top, bw, bh, demo.TEAL if i % 2 else '#4a5a8c')
        for wy in range(int(top) + 18, int(HORIZON) - 22, 30):
            for wx in range(x + 14, x + bw - 20, 28):
                cv.rect(wx, wy, 13, 16, demo.INK, alpha=0.55)
    cv.rect(0, HORIZON, W, H - HORIZON, '#22252d')
    cv.line(0, HORIZON, W, HORIZON, demo.INK, width=3)
    vx = W / 2
    for k in range(-8, 9):
        cv.line(vx + k * 30, HORIZON, vx + k * 170, H, demo.LINE, width=1.5)
    for d in (1.25, 1.8, 3.0, 6.0):
        y = HORIZON + (H - HORIZON) / d
        cv.line(0, y, W, y, demo.LINE, width=1.5)
    demo.dot(cv, W / 2, HORIZON + 50, r=26)


def _draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.9))
    angle = TILT * p
    dutch_angle(cv, _street, angle)
    # A level reference that stays with the frame, not the scene, so the roll reads.
    cv.rect(24, demo.H - 62, 120, 38, (0, 0, 0, 0.55), radius=8)
    demo.word(cv, f'{math.degrees(angle):4.1f}°', 84, demo.H - 43, size=22, font=demo.mono(22))


CAPABILITY = Capability(
    id='dutch-angle',
    name='Dutch angle',
    family='camera',
    group='Camera moves',
    aliases=('Dutch tilt', 'canted angle', 'canted frame', 'Dutch roll', 'oblique angle'),
    definition='The camera tips sideways about its lens, so the horizon and the upright lines in the '
               'shot sit on a slant and the picture feels off balance.',
    phrasings=('tilt the camera so the shot looks crooked',
               'make the frame lean to one side to feel uneasy',
               'roll the view off level so everything is on a diagonal'),
    related=('slant-axis-swing', 'isometric-view', 'angled-lower-third', 'diagonal-wipe', 'globe-spin',
             'bend-deformer'),
    api=('videobuilder.capabilities.camera.dutch_angle.dutch_angle',
         'videobuilder.capabilities.camera.dutch_angle.cover_scale'),
    demo=lambda: demo.film(_draw),
)

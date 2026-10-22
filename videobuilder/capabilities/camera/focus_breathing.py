"""Focus breathing: as focus pulls from a near subject to a far one, the
whole picture creeps a little larger (and shrinks back when focus returns),
the way a real lens's field of view shifts as it focuses."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type.kit import blurred


def _soft(cv, box, radius, paint):
    if radius < 0.5:
        paint(cv)
    else:
        blurred(cv, box, radius, paint)


def focus_breathing(cv, near, far, focus, blur=18, breath=0.07, center=None):
    """Draw a two-depth shot with focus at `focus` (0 = on `near`, 1 = on
    `far`). `far(cv)` and `near(cv)` paint the background and foreground
    layers; the one out of focus is blurred by up to `blur` px, and the whole
    picture is scaled by `1 + breath * focus` about `center` (default the
    frame centre), so racking focus also nudges the framing in. A negative
    `breath` makes the lens breathe out instead.

    In a film, drive `focus` with an eased 0 -> 1 over the rack, e.g.
    `focus_breathing(cv, near, far, vb.ease_in_out_quart(p))`."""
    box = vb.Box.of(cv)
    cx, cy = center or (box.cx, box.cy)
    f = vb.clamp01(focus)
    s = 1 + breath * f
    with cv.clip(box.x, box.y, box.w, box.h):
        with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
            _soft(cv, box, blur * (1 - f), far)
            _soft(cv, box, blur * f, near)


def _far(cv):
    """The back wall: a gridded panel with a ring target on it."""
    W, H = demo.W, demo.H
    x, y, w, h = W * 0.2, H * 0.12, W * 0.6, H * 0.6
    cv.rect(x, y, w, h, '#252b3a', radius=6)
    step = 48
    for i in range(1, int(w // step) + 1):
        cv.line(x + i * step, y, x + i * step, y + h, demo.MUTED, width=2, alpha=0.35)
    for j in range(1, int(h // step) + 1):
        cv.line(x, y + j * step, x + w, y + j * step, demo.MUTED, width=2, alpha=0.35)
    rx, ry, r = W * 0.6, H * 0.34, 110
    cv.sector(rx, ry, r, 0, 2 * math.pi, demo.TEAL)
    cv.sector(rx, ry, r - 22, 0, 2 * math.pi, '#252b3a')
    for k in range(36):
        a = k * math.pi / 18
        cv.line(rx + (r - 40) * math.cos(a), ry + (r - 40) * math.sin(a),
                rx + (r - 30) * math.cos(a), ry + (r - 30) * math.sin(a), demo.INK, width=2)


def _near(cv):
    """The foreground: a floor and a ball sitting on it."""
    W, H = demo.W, demo.H
    cv.rect(0, H * 0.72, W, H * 0.28, '#1c2130')
    cv.line(0, H * 0.72, W, H * 0.72, demo.MUTED, width=3)
    bx, by, r = W * 0.33, H * 0.68, 80
    cv.shadow(bx - r, by + r * 0.75, 2 * r, r * 0.3, radius=r * 0.15, blur=18, color=(0, 0, 0, 0.6))
    demo.dot(cv, bx, by, r=r, color=demo.ACCENT)
    demo.dot(cv, bx - r * 0.3, by - r * 0.35, r=r * 0.22, color=demo.INK, alpha=0.35)


def _brackets(cv):
    """Fixed viewfinder corners, outside the lens, so the framing change reads."""
    W, H, m, a = demo.W, demo.H, 60, 70
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        cv.line(x, y, x + sx * a, y, demo.INK, width=4, alpha=0.8)
        cv.line(x, y, x, y + sy * a, demo.INK, width=4, alpha=0.8)


def _draw(n, cv):
    there = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.3))
    back = vb.ease_in_out_quart(demo.phase(n, 1.9, 2.7))
    focus_breathing(cv, _near, _far, there - back, blur=20, breath=0.08)
    _brackets(cv)


CAPABILITY = Capability(
    id='focus-breathing',
    name='Focus breathing',
    family='camera',
    group='Lens',
    aliases=('lens breathing',),
    definition='When the focus shifts between near and far subjects, the framing quietly '
               'swells or shrinks along with it, as if the lens nudged its zoom.',
    phrasings=('make the shot zoom in a touch as the focus moves to the background',
               'rack focus with that real-lens breathing where the frame shifts size',
               'let the picture grow slightly as it pulls focus, like a cine lens'),
    related=('focus-blur-out', 'optical-zoom', 'zoom-through', 'rack-focus', 'tilt-shift-miniature',
             'dolly-zoom'),
    api=('videobuilder.capabilities.camera.focus_breathing.focus_breathing', 'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(_draw),
)

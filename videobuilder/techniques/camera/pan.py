"""Pan: the camera turns sideways on the spot, so a scene wider than the
frame drifts across it -- what was at one edge ends up at the other."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLIDE = vb.bezier(0.45, 0.0, 0.55, 1.0)   # a gentle start and stop, like a fluid head on a tripod


def pan_x(p, travel, ease=GLIDE):
    """How far the camera has panned at progress `p` (0 -> 1): `ease(p)` of
    `travel` px, clamped to the ends."""
    return travel * ease(vb.clamp01(p))


def pan(cv, scene, p, travel, direction='right', ease=GLIDE):
    """Draw `scene(cv)` through the frame with the camera panned at progress
    `p` (0 -> 1). `scene` paints a panorama in its own px, `cv.width +
    travel` wide, starting at x 0; the camera looks at its left end at
    p = 0 and its right end at p = 1 for `direction='right'` (the picture
    slides left), and the other way round for `'left'`. Clipped to the
    frame, so things drawn past the panorama's ends never show.

    In a film, call it from a shot's draw with the shot's own progress, e.g.
    `pan(cv, lambda c: skyline(c, f), shot.f / shot.frames, travel=1.5 * cv.width)`;
    a slow pan reads best over three seconds or more, eased at both ends."""
    x = pan_x(p, travel, ease)
    if direction == 'left':
        x = travel - x
    elif direction != 'right':
        raise ValueError(f"direction must be 'left' or 'right', not {direction!r}")
    with cv.clip(0, 0, cv.width, cv.height), cv.layer(dx=-x):
        scene(cv)


# ---- the demo: a row of pillars on a gridded floor, panned past a fixed viewfinder ----

TRAVEL = 1.4 * demo.W
HORIZON = demo.H * 0.58
PILLARS = ((0.10, 0.46, demo.TEAL), (0.34, 0.30, demo.MUTED), (0.58, 0.38, demo.MUTED),
           (1.38, 0.34, demo.MUTED), (1.64, 0.26, demo.MUTED), (1.86, 0.46, demo.TEAL),
           (2.20, 0.32, demo.MUTED))
PLINTH = (1.2 * demo.W, HORIZON + 90)


def _panorama(cv):
    w = demo.W + TRAVEL
    cv.fill(demo.BG)
    for i in range(0, math.ceil(w / 120) + 1):
        cv.line(i * 120, HORIZON, i * 120 - (i * 120 - w / 2) * 0.6, demo.H, demo.LINE, width=2)
    for k in range(5):
        y = HORIZON + (demo.H - HORIZON) * (k / 4) ** 1.6
        cv.line(0, y, w, y, demo.LINE, width=2)
    cv.line(0, HORIZON, w, HORIZON, demo.MUTED, width=3)
    for fx, fh, color in PILLARS:
        x, h = fx * demo.W, fh * demo.H
        cv.rect(x - 34, HORIZON - h, 68, h + 40, color, radius=6)
    px, py = PLINTH
    cv.rect(px - 130, py - 20, 260, 120, demo.MUTED, radius=10)
    demo.dot(cv, px, py - 90, r=70)


def _viewfinder(cv):
    m, arm = 60, 70
    for x, y, sx, sy in ((m, m, 1, 1), (demo.W - m, m, -1, 1), (m, demo.H - m, 1, -1),
                         (demo.W - m, demo.H - m, -1, -1)):
        cv.line(x, y, x + sx * arm, y, demo.INK, width=4, alpha=0.8)
        cv.line(x, y, x, y + sy * arm, demo.INK, width=4, alpha=0.8)
    cx, cy = demo.W / 2, demo.H / 2
    cv.line(cx - 24, cy, cx + 24, cy, demo.INK, width=3, alpha=0.6)
    cv.line(cx, cy - 24, cx, cy + 24, demo.INK, width=3, alpha=0.6)


def _demo():
    def draw(n, cv):
        pan(cv, _panorama, demo.phase(n, 0.3, 2.8), TRAVEL)
        _viewfinder(cv)
    return demo.film(draw)


TECHNIQUE = Technique(
    id='pan',
    name='Pan',
    family='camera',
    group='Camera moves',
    aliases=('horizontal pan', 'panning shot', 'pan left', 'pan right'),
    definition='The camera stays put but swings to one side, so the whole scene glides sideways '
               'across the frame and new parts of it come into view.',
    phrasings=('slowly sweep the camera across the scene from left to right',
               'turn the view sideways to reveal the rest of the room',
               'glide across a wide shot that does not fit in one frame'),
    related=('shutter-wipe', 'whip-pan', 'stereo-panning', 'canvas-pan-and-zoom',
             'horizontal-scroll-section', 'spin'),
    api=('videobuilder.techniques.camera.pan.pan', 'videobuilder.techniques.camera.pan.pan_x',
         'videobuilder.Canvas.view'),
    demo=_demo,
)

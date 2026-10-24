"""Dolly in and out: the same idea as Push-in (`push_in.py`), which keeps the
capability -- the camera travels toward the subject; this module only adds
the return trip back out. This module's own code stays (a film may still
import it), but it is no longer a capability of its own."""
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'push-in'


def dolly_scale(depth, z):
    """How much bigger a flat layer `depth` units in front of the camera
    looks once the camera has moved `z` units toward it (1.0 at `z` 0).
    `z` must stay below `depth`: the camera can't pass through the layer."""
    return depth / (depth - z)


@contextmanager
def dolly(cv, depth, z, cx=None, cy=None):
    """Draw a layer as seen by a camera dollied `z` units forward: inside the
    block, paint the layer in its rest position (as at `z` 0) and it comes
    out scaled by `dolly_scale(depth, z)` about the vanishing point (`cx`,
    `cy`), the frame centre by default. Paint far layers first."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    s = dolly_scale(depth, z)
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        yield cv


def dolly_in_out(t, start, peak, hold, back, distance):
    """A camera `z` for an in-and-out move at time `t` (seconds): 0 until
    `start`, eased forward to `distance` by `peak`, held until `hold`, eased
    back to 0 by `back`."""
    go = vb.ease_in_out_quart(vb.clamp01((t - start) / (peak - start)))
    ret = vb.ease_in_out_quart(vb.clamp01((t - hold) / (back - hold)))
    return distance * (go - ret)


W, H = demo.W, demo.H
HORIZON = H * 0.46
FAR, GATE, SUBJECT, NEAR = 9.0, 4.0, 3.0, 1.6     # each layer's distance from the camera at rest
FLOOR = 570                                       # eye height over the floor, times focal length, in px


def _floor(cv, z):
    """Floor lines at fixed depths, so the ground visibly streams past: a line
    `d` units ahead sits `FLOOR / d` px below the horizon."""
    for i in range(1, 40):
        d = i * 0.5 - z
        if d <= 0.2 or HORIZON + FLOOR / d > H:
            continue
        cv.line(0, HORIZON + FLOOR / d, W, HORIZON + FLOOR / d, demo.MUTED, width=2, alpha=min(0.6, 1.2 / d))


def _pillars(cv):
    for x in range(140, W, 220):
        cv.rect(x - 22, HORIZON - 260, 44, 260 + FLOOR / FAR, '#2a2f38', radius=4)
    cv.rect(0, HORIZON - 60, W, 14, '#2a2f38')


def _gate(cv):
    cx, top = W / 2, HORIZON - 230
    cv.rect(cx - 250, top, 500, 34, demo.TEAL, radius=6)
    cv.rect(cx - 230, top + 34, 40, 196 + FLOOR / GATE, demo.TEAL, radius=4)
    cv.rect(cx + 190, top + 34, 40, 196 + FLOOR / GATE, demo.TEAL, radius=4)


def _subject(cv):
    cx, y = W / 2, HORIZON + FLOOR / SUBJECT - 120
    cv.shadow(cx - 110, y, 220, 120, radius=8, dy=10, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(cx - 110, y, 220, 120, '#3a404b', radius=8)
    demo.dot(cv, cx, y - 58, r=58)


def _near(cv):
    for x in (230, W - 230):
        cv.rect(x - 40, HORIZON - 340, 80, 340 + FLOOR / NEAR, '#1c2027', radius=6)


def draw(n, cv):
    z = dolly_in_out(n / demo.FPS, 0.3, 1.35, 1.65, 2.75, 1.1)
    _floor(cv, z)
    for depth, paint in ((FAR, _pillars), (GATE, _gate), (SUBJECT, _subject), (NEAR, _near)):
        with dolly(cv, depth, z, cy=HORIZON):
            paint(cv)

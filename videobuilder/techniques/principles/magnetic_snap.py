"""Magnetic Snap: something drifts along freely until it comes within reach of
a target, leans toward it, then is yanked onto it and lands with a springy
overshoot -- the feel of a magnet catching a piece of metal."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def magnetic_snap(path, target, t, radius=140.0, lean=0.35, ratio=0.4, hz=3.0, step=1 / 240):
    """Where a thing drifting along `path` is drawn at `t` seconds when a magnet
    sits at `target`. Returns `(x, y, caught)`, where `caught` is the seconds
    since it was grabbed (negative before).

    `path(t) -> (x, y)` is the free motion. Inside `2 * radius` the thing leans
    up to `lean` of the way toward `target`; the first time the free path comes
    within `radius` it is caught, and from then on it springs from where it was
    caught onto `target` (`vb.damped(ratio, hz)`: lower `ratio`, more wobble).
    Pure: the catch time is found by stepping along `path`, so any `t` evaluates
    alone."""
    tx, ty = target

    def leaned(s):
        x, y = path(s)
        d = math.hypot(x - tx, y - ty)
        k = lean * vb.clamp01(2 - d / radius) ** 2  # 0 at 2 * radius, `lean` at the edge of capture
        return x + (tx - x) * k, y + (ty - y) * k

    s = 0.0
    while s <= t:
        x, y = path(s)
        if math.hypot(x - tx, y - ty) <= radius:
            cx, cy = leaned(s)
            p = vb.spring(t - s, **vb.damped(ratio, hz))
            return cx + (tx - cx) * p, cy + (ty - cy) * p, t - s
        s += step
    x, y = leaned(t)
    return x, y, -1.0


SLOT = (demo.W * 0.68, demo.H * 0.55)
RADIUS = 110
CARD_W, CARD_H = 200, 124


def drift(t):
    """The card's free path: a slow diagonal drift, wobbling a little, that passes near the slot."""
    return 120 + 260 * t, 170 + 60 * t + 14 * math.sin(t * 4.0)


def draw(n, cv):
    sx, sy = SLOT
    x, y, caught = magnetic_snap(drift, SLOT, n / demo.FPS, radius=RADIUS)
    flash = math.exp(-caught * 6) if caught >= 0 else 0.0
    # the magnet's reach, and the slot it pulls into
    cv.arc(sx, sy, RADIUS, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.25 + 0.6 * flash)
    if flash:
        cv.arc(sx, sy, RADIUS * (1 + 0.5 * (1 - flash)), 0, 2 * math.pi, demo.ACCENT, width=4, alpha=flash)
    cv.outline(sx - CARD_W / 2, sy - CARD_H / 2, CARD_W, CARD_H, demo.ACCENT if caught >= 0 else demo.MUTED,
               width=3, radius=18, alpha=0.5 + 0.5 * flash)
    if caught < 0:  # the free path it would have kept on, while it is still loose
        fx, fy = drift(n / demo.FPS + 0.6)
        cv.line(x, y, fx, fy, demo.MUTED, width=2, alpha=0.3)
    demo.card(cv, x, y, w=CARD_W, h=CARD_H, color=demo.TEAL if caught < 0 else demo.ACCENT)


TECHNIQUE = Technique(
    id='magnetic-snap',
    name='Magnetic Snap',
    family='principles',
    group='Physics',
    aliases=('snap to target', 'magnetic pull', 'snap into place', 'dock snap'),
    definition='Something moving loosely drifts close to a target, gets tugged toward it, '
               'then jumps the last stretch and locks on with a small springy wobble.',
    phrasings=('make the card get sucked into the slot when it gets close',
               'it should snap into place like a magnet grabbed it',
               'drift near the spot and then click onto it'),
    related=('magnetic-button', 'gravity-well-attraction', 'momentum-fling', 'punch-in',
             'spring-drag-letters', 'bounce-ease-in'),
    api=('videobuilder.techniques.principles.magnetic_snap.magnetic_snap', 'videobuilder.spring',
         'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)

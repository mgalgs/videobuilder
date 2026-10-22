"""Cursor follower dot and ring: a small dot sits exactly on the pointer while
a wider ring chases it with an eased lag, falling behind on quick moves and
closing back around the dot when the pointer rests."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def follow(path, t, lag=0.14, step=1 / 120):
    """Where a follower chasing `path` is at `t` seconds. `path(t)` gives the
    pointer's (x, y); the follower starts on it at t = 0 and closes the gap
    exponentially, `lag` seconds being the time to cover ~63% of it. Stepped
    from 0 every call, so any frame renders the same on its own."""
    x, y = path(0.0)
    k = 1 - math.exp(-step / lag) if lag > 0 else 1.0
    s = 0.0
    while s + step <= t:
        s += step
        tx, ty = path(s)
        x, y = x + (tx - x) * k, y + (ty - y) * k
    return x, y


def draw_cursor_follower(cv, path, t, lag=0.14, dot_r=9, ring_r=34, color=demo.INK, ring_color=None,
                         ring_width=2.5, alpha=1.0):
    """Draw the dot on `path(t)` and the ring lagging behind it (see `follow`).
    `ring_color` defaults to `color`. Returns ((dot x, y), (ring x, y))."""
    px, py = path(t)
    rx, ry = follow(path, t, lag)
    cv.arc(rx, ry, ring_r, 0, 2 * math.pi, ring_color or color, width=ring_width, alpha=alpha)
    demo.dot(cv, px, py, r=dot_r, color=color, alpha=alpha)
    return (px, py), (rx, ry)


# The demo pointer: quick eased darts between resting spots, so the ring trails on
# each move and settles back around the dot at each stop.
STOPS = ((0.0, 0.22, 0.6), (0.35, 0.22, 0.6), (0.85, 0.68, 0.3), (1.15, 0.68, 0.3),
         (1.6, 0.4, 0.76), (1.9, 0.4, 0.76), (2.35, 0.78, 0.64), (3.0, 0.78, 0.64))


def demo_path(t):
    ts = [s[0] for s in STOPS]
    ease = vb.ease_in_out_quart
    return (demo.W * vb.interpolate(t, ts, [s[1] for s in STOPS], ease=ease),
            demo.H * vb.interpolate(t, ts, [s[2] for s in STOPS], ease=ease))


def draw(n, cv):
    (px, py), (rx, ry) = draw_cursor_follower(cv, demo_path, n / demo.FPS, lag=0.12, dot_r=6, ring_r=24,
                                              color=demo.ACCENT, ring_color=demo.INK, ring_width=2)
    cv.mark('ring', rx - 24, ry - 24, 48, 48)


TECHNIQUE = Technique(
    id='cursor-follower-dot-and-ring',
    name='Cursor follower dot and ring',
    family='ui',
    group='Cursor & hover',
    aliases=('lagging cursor', 'trailing ring', 'custom cursor follower'),
    definition='A custom pointer made of a dot that sits right on the mouse and an outline ring '
               'that drifts after it, trailing on fast moves and re-centring when it stops.',
    phrasings=('a cursor dot with a circle that follows it a beat behind',
               'the ring around the mouse lags and catches up smoothly',
               'custom pointer where an outer circle chases the dot'),
    related=('cursor-path-animation', 'dot-grid-displacement', 'proximity-stagger', 'blinking-cursor',
             'bouncing-dots', 'magnetic-button'),
    api=('videobuilder.techniques.ui.cursor_follower_dot_and_ring.draw_cursor_follower',
         'videobuilder.techniques.ui.cursor_follower_dot_and_ring.follow'),
    demo=lambda: demo.film(draw),
)

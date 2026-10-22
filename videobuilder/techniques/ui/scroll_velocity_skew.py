"""Scroll Velocity Skew: content leans over and stretches while a list scrolls
fast, by an amount that follows the scroll speed, and straightens back up as
the scroll comes to rest."""
import math
from contextlib import contextmanager

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def velocity_skew(velocity, max_degrees=8.0, per_degree=150.0, max_stretch=0.08):
    """Scroll `velocity` in px/s -> `(skew_degrees, stretch)`. The lean grows
    with speed and saturates at `max_degrees` (one degree per `per_degree`
    px/s while slow); its sign follows the scroll direction. `stretch` is the
    extra length along the scroll axis, 0 at rest up to `max_stretch`."""
    k = math.tanh(velocity / (per_degree * max_degrees))
    return max_degrees * k, max_stretch * abs(k)


def scroll_velocity(position, t, dt=1 / 60):
    """The speed in px/s of a scroll offset `position(t)` (t in seconds) at
    `t`, by a central difference. Feed it to `velocity_skew`."""
    return (position(t + dt / 2) - position(t - dt / 2)) / dt


@contextmanager
def skewed(cv, cx, cy, degrees, stretch=0.0, axis='y'):
    """Draw inside the block sheared by `degrees` and stretched by `stretch`
    about (cx, cy). `axis='y'` suits a vertical scroll (horizontal edges
    tilt, height grows); `axis='x'` a horizontal one."""
    s = math.tan(math.radians(degrees))
    if axis == 'y':
        m = cairo.Matrix(1, s, 0, 1 + stretch, 0, 0)
    else:
        m = cairo.Matrix(1 + stretch, 0, s, 1, 0, 0)
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.transform(m)
    c.translate(-cx, -cy)
    try:
        yield
    finally:
        c.restore()


GAP, CARD_W, CARD_H = 18, 300, 112
COLORS = (demo.ACCENT, demo.TEAL, '#7b7fff', '#e7b84b')
PANEL_W, PANEL_H = 420, 470
TRAVEL = 800


def _position(t):
    """The demo's scroll offset: rest, a hard flick down, rest, a flick back up."""
    down = vb.ease_in_out_quart(demo.phase(t * demo.FPS, 0.35, 1.45))
    up = vb.ease_in_out_quart(demo.phase(t * demo.FPS, 1.85, 2.7))
    return TRAVEL * down - 480 * up


def draw(n, cv):
    t = n / demo.FPS
    offset = _position(t)
    degrees, stretch = velocity_skew(scroll_velocity(_position, t))
    px, py = (demo.W - PANEL_W) / 2, (demo.H - PANEL_H) / 2
    cv.rect(px, py, PANEL_W, PANEL_H, '#14161c', radius=16)
    cv.outline(px, py, PANEL_W, PANEL_H, demo.LINE, width=2, radius=16)
    c = cv.ctx
    c.save()
    c.rectangle(px, py, PANEL_W, PANEL_H)
    c.clip()
    pitch = CARD_H + GAP
    first = int((offset - GAP) // pitch)
    for i in range(first, first + int(PANEL_H // pitch) + 3):
        cy = py + GAP + CARD_H / 2 + i * pitch - offset
        with skewed(cv, demo.W / 2, cy, degrees, stretch):
            demo.card(cv, demo.W / 2 - 10, cy, w=CARD_W, h=CARD_H, color=COLORS[i % len(COLORS)])
    c.restore()
    # scrollbar: a fixed track with a thumb that follows the offset
    track = PANEL_H - 40
    thumb = 70
    tx = px + PANEL_W - 18
    cv.rect(tx, py + 20, 4, track, demo.LINE, radius=2)
    cv.rect(tx - 1, py + 20 + (track - thumb) * offset / TRAVEL, 6, thumb, demo.INK, radius=3)
    cv.mark('list', px, py, PANEL_W, PANEL_H)


TECHNIQUE = Technique(
    id='scroll-velocity-skew',
    name='Scroll velocity skew',
    family='ui',
    group='Scroll',
    aliases=('velocity distortion', 'speed-based skew', 'scroll skew'),
    definition='While a page scrolls, its items lean and stretch more the faster it moves, '
               'then settle back square once the scrolling stops.',
    phrasings=('make the cards tilt when you scroll quickly and straighten when it stops',
               'the list bends with the speed of the scroll',
               'items shear a little as they whip past, like they are being dragged'),
    related=('rolling-shutter-wobble', 'momentum-fling', 'timeline-scroll', 'tape-wobble', 'motion-blur',
             'frame-stutter'),
    api=('videobuilder.techniques.ui.scroll_velocity_skew.velocity_skew',
         'videobuilder.techniques.ui.scroll_velocity_skew.skewed',
         'videobuilder.techniques.ui.scroll_velocity_skew.scroll_velocity'),
    demo=lambda: demo.film(draw),
)

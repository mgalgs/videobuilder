"""Cursor Path Animation: a mouse pointer travels a gently curved route from
one interface target to the next, pausing on each to click (a quick press and
a ring), the way a product walkthrough shows where to go."""
import math
from collections import namedtuple

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# A pointer arrow, tip at (0, 0), in pixels at scale 1.
ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))

CursorPose = namedtuple('CursorPose', 'x y stop click')
CursorPose.__doc__ = """Where the cursor is at one moment: tip at (`x`, `y`);
`stop` is the index of the target it last reached (0 before it leaves the
start); `click` is that click's progress 0 -> 1 while it rests on a target
(stop >= 1), else -1 while travelling or before the first move."""


def _bend(a, b, bend, u):
    """Point `u` (0 -> 1) along a quadratic curve from `a` to `b` whose
    control point sits `bend` x the hop length off the straight line."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2 - dy * bend, (y0 + y1) / 2 + dx * bend
    v = 1 - u
    return v * v * x0 + 2 * v * u * cx + u * u * x1, v * v * y0 + 2 * v * u * cy + u * u * y1


def cursor_path(stops, t, start=0.0, travel=0.6, dwell=0.35, bend=0.22, ease=vb.ease_in_out_quart):
    """The cursor's `CursorPose` at time `t` seconds for a walkthrough over
    `stops`, a list of (x, y) tips: it rests on `stops[0]` until `start`, then
    for each next stop glides `travel` seconds along a curve bowed sideways by
    `bend` (a fraction of the hop; negative bows the other way), shaped by
    `ease`, and rests `dwell` seconds there while its click plays. After the
    last stop it stays put with its click finished."""
    if len(stops) < 2:
        x, y = stops[0]
        return CursorPose(x, y, 0, -1.0)
    t -= start
    if t < 0:
        return CursorPose(*stops[0], 0, -1.0)
    hop = travel + dwell
    i = min(int(t // hop), len(stops) - 2)
    local = t - i * hop
    if local < travel:
        x, y = _bend(stops[i], stops[i + 1], bend, ease(vb.clamp01(local / travel)))
        return CursorPose(x, y, i, -1.0)
    x, y = stops[i + 1]
    return CursorPose(x, y, i + 1, vb.clamp01((local - travel) / dwell) if dwell > 0 else 1.0)


def cursor_trail(stops, t, start=0.0, travel=0.6, dwell=0.35, bend=0.22, ease=vb.ease_in_out_quart, step=1 / 60):
    """The route the cursor of `cursor_path` (same arguments) has covered by
    time `t`, sampled every `step` seconds, as a point list for
    `videobuilder.paths.draw` or a dotted trail."""
    pts = []
    s = start
    while s < t:
        p = cursor_path(stops, s, start, travel, dwell, bend, ease)
        if not pts or (p.x, p.y) != pts[-1]:
            pts.append((p.x, p.y))
        s += step
    p = cursor_path(stops, t, start, travel, dwell, bend, ease)
    pts.append((p.x, p.y))
    return pts


def draw_cursor(cv, pose, scale=1.4, color=demo.INK, edge=demo.BG):
    """Draw an arrow pointer at `pose` (a `CursorPose`, or anything with x, y
    and click), dipping slightly while it clicks, with a ring spreading from
    the tip."""
    click = getattr(pose, 'click', -1.0)
    press = 1 - 0.14 * math.sin(math.pi * vb.clamp01(click / 0.45)) if click >= 0 else 1.0
    if 0 <= click < 1:
        ring = vb.ease_out_expo(click)
        cv.arc(pose.x, pose.y, 8 + 34 * ring, 0, 2 * math.pi, color, width=3, alpha=0.75 * (1 - click))
    s = scale * press
    pts = [(pose.x + px * s, pose.y + py * s) for px, py in ARROW]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    ctx = cv.ctx
    ctx.new_path()
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(edge))
    ctx.set_line_width(2)
    ctx.stroke()


# The demo: a settings panel with a button, a toggle and a checkbox.
PX, PY, PW, PH = demo.W / 2 - 330, demo.H / 2 - 170, 660, 340
BUTTON = (PX + 50, PY + 220, 170, 70)
TOGGLE = (PX + 440, PY + 232, 96, 46)
CHECK = (PX + 580, PY + 40, 40, 40)
STOPS = [(160, demo.H - 90),
         (BUTTON[0] + 110, BUTTON[1] + 40),
         (TOGGLE[0] + 34, TOGGLE[1] + 26),
         (CHECK[0] + 22, CHECK[1] + 24)]
TIMING = dict(start=0.3, travel=0.55, dwell=0.3, bend=0.25)


def _hit(n, stop):
    """0 -> 1 as the click on `stop` lands, held at 1 after."""
    hop = TIMING['travel'] + TIMING['dwell']
    at = TIMING['start'] + (stop - 1) * hop + TIMING['travel']
    return demo.phase(n, at, at + 0.15)


def _panel(cv, n):
    cv.shadow(PX, PY, PW, PH, radius=22, dy=12, blur=32, color=(0, 0, 0, 0.45))
    cv.rect(PX, PY, PW, PH, '#1d1f26', radius=22)
    for i, w in enumerate((300, 400, 240)):
        cv.rect(PX + 50, PY + 46 + i * 34, w, 12, demo.MUTED, radius=6, alpha=0.55 - 0.12 * i)
    x, y, w, h = BUTTON
    b = _hit(n, 1)
    cv.rect(x, y, w, h, demo.kit.mix(demo.ACCENT, '#ff8a7c', b * (1 - b) * 4), radius=14)
    demo.word(cv, 'Start', x + w / 2, y + h / 2, size=30, weight=700)
    x, y, w, h = TOGGLE
    k = vb.ease_out_back(_hit(n, 2))
    cv.rect(x, y, w, h, demo.kit.mix(demo.LINE, demo.TEAL, vb.clamp01(k)), radius=h / 2)
    demo.dot(cv, x + h / 2 + (w - h) * k, y + h / 2, h / 2 - 6, color=demo.INK)
    x, y, w, h = CHECK
    c = _hit(n, 3)
    cv.rect(x, y, w, h, demo.kit.mix(demo.LINE, demo.TEAL, c), radius=8)
    if c > 0:
        tick = [(x + 9, y + 21), (x + 17, y + 29), (x + 32, y + 12)]
        vb.paths.draw(cv, vb.paths.reveal(tick, c), demo.INK, width=4)


def draw(n, cv):
    t = n / demo.FPS
    _panel(cv, n)
    trail = cursor_trail(STOPS, t, **TIMING)
    for i, (x, y) in enumerate(vb.paths.resample(trail, max(2, int(vb.paths.length(trail) / 18)))):
        demo.dot(cv, x, y, 3, color=demo.INK, alpha=0.35)
    pose = cursor_path(STOPS, t, **TIMING)
    draw_cursor(cv, pose)
    cv.mark('cursor', pose.x, pose.y, 30, 45)


TECHNIQUE = Technique(
    id='cursor-path-animation',
    name='Cursor path animation',
    family='broadcast',
    group='UI walkthroughs',
    aliases=('mouse path', 'pointer trajectory', 'cursor walkthrough'),
    definition='A mouse pointer sweeps along smooth curves from one on-screen control to the next, '
               'stopping on each to click before moving on.',
    phrasings=('show a mouse moving around the screen clicking the buttons',
               'animate the pointer going from the button to the toggle to the checkbox',
               'a fake cursor that walks the viewer through the interface'),
    related=('cursor-particle-trail', 'cursor-state-change', 'cursor-follower-dot-and-ring',
             'magnetic-button', 'arrow-pointer-draw', 'proximity-stagger'),
    api=('videobuilder.techniques.broadcast.cursor_path_animation.cursor_path',
         'videobuilder.techniques.broadcast.cursor_path_animation.draw_cursor',
         'videobuilder.techniques.broadcast.cursor_path_animation.cursor_trail'),
    demo=lambda: demo.film(draw),
)

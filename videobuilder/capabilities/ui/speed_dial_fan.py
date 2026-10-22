"""Speed dial fan: a round floating action button turns its plus into a cross
while a handful of smaller action buttons pop out of it one after another,
spreading along an arc."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def fan_layout(n, p, distance=130, start=math.pi, end=1.5 * math.pi, stagger=0.18):
    """Where the `n` fanned buttons are at progress `p` (0 closed -> 1 open):
    a list of `(dx, dy, scale)` offsets from the main button's centre, first
    button first. They sit evenly on an arc of radius `distance` from angle
    `start` to `end` (radians, canvas convention: pi is left, 1.5 pi is up).
    Each starts `stagger` of the run after the one before and overshoots a
    little as it lands; run `p` backwards to close, last one in first."""
    out = []
    span = 1 - stagger * (n - 1) if n > 1 else 1
    for i in range(n):
        q = vb.clamp01((p - stagger * i) / span)
        k = vb.ease_out_back(q) if q > 0 else 0.0
        a = start + (end - start) * (i / (n - 1) if n > 1 else 0.5)
        out.append((math.cos(a) * distance * k, math.sin(a) * distance * k, max(0.0, k)))
    return out


def _plus(cv, cx, cy, size, color, angle=0.0, width=4):
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(angle)
    cv.line(-size, 0, size, 0, color, width=width)
    cv.line(0, -size, 0, size, color, width=width)
    c.restore()


def _icon_circle(cv, cx, cy, s, color):
    cv.arc(cx, cy, s * 0.8, 0, 2 * math.pi, color, width=2.5)


def _icon_square(cv, cx, cy, s, color):
    cv.outline(cx - s * 0.75, cy - s * 0.75, s * 1.5, s * 1.5, color, width=2.5, radius=s * 0.25)


def _icon_triangle(cv, cx, cy, s, color):
    pts = [(cx, cy - s * 0.85), (cx + s * 0.85, cy + s * 0.6), (cx - s * 0.85, cy + s * 0.6)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cv.line(x0, y0, x1, y1, color, width=2.5)


def _icon_plus(cv, cx, cy, s, color):
    _plus(cv, cx, cy, s * 0.8, color, width=2.5)


ICONS = (_icon_square, _icon_plus, _icon_triangle, _icon_circle)


def draw_speed_dial(cv, cx, cy, p, icons=ICONS, r=36, item_r=24, color=demo.ACCENT, item_color=demo.LINE,
                    ink=demo.INK, **layout):
    """Draw a speed dial whose main button is centred at (cx, cy), at
    progress `p` (0 closed -> 1 open). The main button's plus turns 45 degrees
    into a cross; one small button per entry of `icons` (each
    `icon(cv, cx, cy, size, color)`) fans out behind it. `layout` goes to
    `fan_layout`. Marks `fab` and `action-<i>`; returns the item centres."""
    centres = []
    for i, ((dx, dy, s), icon) in enumerate(zip(fan_layout(len(icons), p, **layout), icons)):
        x, y = cx + dx, cy + dy
        centres.append((x, y))
        if s <= 0:
            continue
        rr = item_r * s
        with cv.layer(opacity=vb.clamp01(s * 2)):
            cv.shadow(x - rr, y - rr, 2 * rr, 2 * rr, radius=rr, dy=4 * s, blur=12 * s, color=(0, 0, 0, 0.4))
            demo.dot(cv, x, y, rr, color=item_color)
            icon(cv, x, y, item_r * 0.38 * s, ink)
        cv.mark(f'action-{i}', x - rr, y - rr, 2 * rr, 2 * rr)
    cv.shadow(cx - r, cy - r, 2 * r, 2 * r, radius=r, dy=5, blur=16, color=(0, 0, 0, 0.5))
    demo.dot(cv, cx, cy, r, color=color)
    turn = vb.ease_out_back(vb.clamp01(p * 1.6)) if p > 0 else 0.0
    _plus(cv, cx, cy, r * 0.36, ink, angle=turn * math.pi / 4, width=4)
    cv.mark('fab', cx - r, cy - r, 2 * r, 2 * r)
    return centres


def draw(n, cv):
    demo.card(cv, demo.W * 0.34, demo.H * 0.34, w=340, h=190, color=demo.LINE)
    p = demo.phase(n, 0.4, 1.3) - demo.phase(n, 2.1, 2.8)
    draw_speed_dial(cv, demo.W - 170, demo.H - 110, p)


CAPABILITY = Capability(
    id='speed-dial-fan',
    name='Speed dial fan',
    family='ui',
    group='Overlays & menus',
    aliases=('fab menu', 'expanding action button', 'speed dial'),
    definition='A round floating button spins its plus into a cross as a few smaller action buttons '
               'pop out of it in turn and spread along an arc.',
    phrasings=('tap the round plus button and little option buttons fan out around it',
               'a floating action button that opens into a ring of mini buttons',
               'the plus turns into an x and the extra actions pop out one by one'),
    related=('plus-to-close-rotate', 'hover-lift', 'liquid-button', 'magnetic-button', 'turntable-rotation',
             'spin'),
    api=('videobuilder.capabilities.ui.speed_dial_fan.draw_speed_dial',
         'videobuilder.capabilities.ui.speed_dial_fan.fan_layout'),
    demo=lambda: demo.film(draw),
)

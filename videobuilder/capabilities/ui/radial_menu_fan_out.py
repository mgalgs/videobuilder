"""Radial Menu Fan-out: a round trigger button is pressed, its plus turns into
a cross, and a ring of smaller option buttons springs out from behind it along
an arc, one after another."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def fan_out(count, p, radius, start=-math.pi, spread=math.pi, stagger=0.45, ease=vb.ease_out_back):
    """Where each of `count` menu items sits at progress `p` (0 closed -> 1
    open), as `(dx, dy, s)` offsets from the trigger's centre plus a 0 -> 1
    scale. Items are spaced evenly over `spread` radians from angle `start`
    (canvas convention: clockwise from +x; the default is the upper half).
    Each item starts `stagger` of the way later than the one before it, so
    the ring opens in sequence; running `p` backwards closes it in reverse."""
    out = []
    for i in range(count):
        a = start + (spread * (i + 0.5) / count if spread < 2 * math.pi else spread * i / count)
        lag = stagger * i / max(count - 1, 1)
        q = vb.clamp01((p - lag) / (1 - stagger)) if stagger < 1 else vb.clamp01(p)
        d = radius * ease(q)
        out.append((d * math.cos(a), d * math.sin(a), vb.clamp01(q * 1.6)))
    return out


def draw_radial_menu(cv, cx, cy, p, items, radius=230, size=84, trigger=120, color=demo.ACCENT,
                     ink=demo.INK, **kw):
    """Draw a radial menu around a trigger button centred at (cx, cy) at
    progress `p`. `items` is a list of `(color, icon)` pairs, where
    `icon(cv, x, y, r)` draws a glyph inside a button of radius `r` (or None).
    The trigger's plus turns 45 degrees into a cross as the menu opens.
    `kw` goes to `fan_out`."""
    for (dx, dy, s), (c, icon) in zip(fan_out(len(items), p, radius, **kw), items):
        if s <= 0:
            continue
        x, y, r = cx + dx, cy + dy, size / 2 * s
        cv.line(cx, cy, x, y, ink, width=2, alpha=0.12 * s)   # a faint spoke back to the trigger
        cv.shadow(x - r, y - r, 2 * r, 2 * r, radius=r, dy=6 * s, blur=18 * s, color=(0, 0, 0, 0.4))
        demo.dot(cv, x, y, r, c)
        if icon:
            icon(cv, x, y, r)
        cv.mark('item', x - r, y - r, 2 * r, 2 * r)
    r = trigger / 2
    cv.shadow(cx - r, cy - r, 2 * r, 2 * r, radius=r, dy=10, blur=26, color=(0, 0, 0, 0.45))
    demo.dot(cv, cx, cy, r, color)
    turn = math.pi / 4 * vb.ease_out_back(vb.clamp01(p * 2))
    arm = r * 0.45
    for k in range(2):
        a = turn + k * math.pi / 2
        ex, ey = arm * math.cos(a), arm * math.sin(a)
        cv.line(cx - ex, cy - ey, cx + ex, cy + ey, ink, width=r * 0.14)
    cv.mark('trigger', cx - r, cy - r, 2 * r, 2 * r)


def _ring(cv, x, y, r):
    cv.arc(x, y, r * 0.38, 0, 2 * math.pi, demo.INK, width=r * 0.12)


def _square(cv, x, y, r):
    s = r * 0.7
    cv.rect(x - s / 2, y - s / 2, s, s, demo.INK, radius=s * 0.18)


def _dot(cv, x, y, r):
    demo.dot(cv, x, y, r * 0.24, demo.INK)


def _bars(cv, x, y, r):
    for k in (-1, 0, 1):
        cv.line(x - r * 0.4, y + k * r * 0.3, x + r * 0.4, y + k * r * 0.3, demo.INK, width=r * 0.12)


def _play(cv, x, y, r):
    c = cv.ctx
    c.new_path()
    c.move_to(x - r * 0.25, y - r * 0.38)
    c.line_to(x + r * 0.42, y)
    c.line_to(x - r * 0.25, y + r * 0.38)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(demo.INK))
    c.fill()


ITEMS = [('#5b8def', _ring), (demo.TEAL, _square), ('#e0a43a', _dot), ('#b46be0', _bars), ('#e05a7a', _play)]


def draw(n, cv):
    p = demo.phase(n, 0.5, 1.4) - demo.phase(n, 2.3, 2.85)
    draw_radial_menu(cv, demo.W / 2, demo.H / 2 + 120, p, ITEMS, radius=270, size=96, trigger=130)


TECHNIQUE = Technique(
    id='radial-menu-fan-out',
    name='Radial menu fan-out',
    family='ui',
    group='Overlays & menus',
    aliases=('radial menu', 'pie menu', 'circular menu', 'floating action menu', 'speed dial'),
    definition='Tapping a round button sends a set of smaller option buttons springing out around it '
               'in an arc, one after another, while its plus icon turns into a close cross.',
    phrasings=('the button opens and little icons pop out around it in a semicircle',
               'menu options burst out of the floating button in a fan',
               'tap the plus and the choices spread out in a circle around it'),
    related=('hamburger-to-x', 'circle-pop', 'plus-to-close-rotate', 'circle-check-draw', 'pie-sweep',
             'sound-reactive-radial-shape'),
    api=('videobuilder.techniques.ui.radial_menu_fan_out.draw_radial_menu',
         'videobuilder.techniques.ui.radial_menu_fan_out.fan_out'),
    demo=lambda: demo.film(draw),
)

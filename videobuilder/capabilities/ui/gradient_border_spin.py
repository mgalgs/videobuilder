"""Gradient Border Spin: a band of colour runs round a card's edge, over and
over -- a conic gradient centred on the card, turning, seen only through
the card's rounded outline."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

VIOLET = '#8b7cf6'
GOLD = '#f2c46d'
# (position 0 -> 1 round the circle, colour, alpha): a bright head with a
# fading tail, then the rest of the edge left dim.
STOPS = ((0.0, demo.TEAL, 0.0), (0.18, demo.TEAL, 0.9), (0.3, VIOLET, 1.0), (0.42, GOLD, 1.0),
         (0.5, GOLD, 0.0), (1.0, demo.TEAL, 0.0))


def _rounded(c, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()


def _colour_at(stops, u):
    u %= 1.0
    for (u0, c0, a0), (u1, c1, a1) in zip(stops, stops[1:]):
        if u0 <= u <= u1:
            t = 0 if u1 == u0 else (u - u0) / (u1 - u0)
            p, q = vb.rgba(c0, a0), vb.rgba(c1, a1)
            return tuple(a + (b - a) * t for a, b in zip(p, q))
    return vb.rgba(stops[-1][1], stops[-1][2])


def conic(cx, cy, radius, stops=STOPS, angle=0.0, wedges=96):
    """A cairo pattern: a conic (sweep) gradient about (cx, cy), out to
    `radius`, rotated by `angle` radians (clockwise). `stops` are
    `(position 0 -> 1 round the circle, colour, alpha)`, first at 0 and last
    at 1; make the ends match for a seamless loop."""
    mesh = cairo.MeshPattern()
    for i in range(wedges):
        u0, u1 = i / wedges, (i + 1) / wedges
        a0, a1 = angle + 2 * math.pi * u0, angle + 2 * math.pi * u1
        mesh.begin_patch()
        mesh.move_to(cx, cy)
        mesh.line_to(cx + radius * math.cos(a0), cy + radius * math.sin(a0))
        mesh.line_to(cx + radius * math.cos(a1), cy + radius * math.sin(a1))
        mesh.line_to(cx, cy)
        for corner, u in enumerate((u0, u0, u1, u1)):
            mesh.set_corner_color_rgba(corner, *_colour_at(stops, u))
        mesh.end_patch()
    return mesh


def gradient_border(cv, x, y, w, h, p, stops=STOPS, width=3, radius=18, glow=10, turns=1.0, base=demo.LINE):
    """Stroke the rounded box (x, y, w, h) with a conic gradient that has
    turned `turns` times round it at progress `p` (0 -> 1; loop `p` for a
    continuous spin). `base` draws a plain edge underneath (None for none);
    `glow` widens a faint halo of the same gradient, in px (0 for none)."""
    c = cv.ctx
    if base:
        cv.outline(x, y, w, h, base, width=width, radius=radius)
    cx, cy = x + w / 2, y + h / 2
    pattern = conic(cx, cy, math.hypot(w, h), stops, angle=2 * math.pi * turns * p - math.pi / 2)
    c.save()
    for extra, alpha in ((glow, 0.12), (glow * 0.5, 0.22), (0, 1.0)) if glow else ((0, 1.0),):
        c.push_group()
        c.set_source(pattern)
        _rounded(c, x, y, w, h, radius)
        c.set_line_width(width + extra)
        c.stroke()
        c.pop_group_to_source()
        c.paint_with_alpha(alpha)
    c.restore()


def draw(n, cv):
    w, h = 460, 270
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cv.shadow(x, y, w, h, radius=20, dy=12, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, '#1d1f27', radius=20)
    cv.rect(x + 36, y + 40, 170, 14, demo.MUTED, radius=7, alpha=0.8)
    cv.rect(x + 36, y + 70, 280, 10, demo.MUTED, radius=5, alpha=0.45)
    cv.rect(x + 36, y + 92, 230, 10, demo.MUTED, radius=5, alpha=0.45)
    cv.rect(x + 36, y + h - 82, 120, 44, VIOLET, radius=10)
    gradient_border(cv, x, y, w, h, n / (demo.FPS * demo.SECONDS), width=4, radius=20, turns=2)
    cv.mark('card', x, y, w, h)


TECHNIQUE = Technique(
    id='gradient-border-spin',
    name='Gradient border spin',
    family='ui',
    group='Cards & media',
    aliases=('conic border spin', 'rotating edge light', 'spinning gradient border'),
    definition='A streak of blended colour chases round and round the outline of a card, '
               'lighting each stretch of the edge as it passes.',
    phrasings=('make a glowing gradient run around the border of the card',
               'a light that keeps circling the edge of the box',
               'give the panel an animated rainbow outline that spins'),
    related=('animated-gradient-sweep', 'spin', 'border-glow-follow', 'rim-light',
             'gradient-sweep-across-text', 'gradient-shift-button'),
    api=('videobuilder.techniques.ui.gradient_border_spin.gradient_border',
         'videobuilder.techniques.ui.gradient_border_spin.conic'),
    demo=lambda: demo.film(draw),
)

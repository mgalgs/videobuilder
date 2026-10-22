"""Glow button: a coloured halo swells out from behind a button when the
pointer arrives, its edge lights up, and the halo keeps breathing softly
for as long as the button stays hovered."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...canvas import rgba
from ..schema import Technique

# An arrow pointer, tip at (0, 0), in px at scale 1.
POINTER = ((0, 0), (0, 30), (7, 23), (12, 35), (17, 33), (12, 21), (22, 21))


def glow_button(cv, x, y, w, h, label, font, hover, t=0.0, color=demo.TEAL, fill='#1d1f26',
                ink=demo.INK, radius=None, reach=40, pulse=0.25, hz=0.9):
    """Draw a button in the box (x, y, w, h) with its glow at `hover` (0 = at
    rest, 1 = fully hovered; ease it in yourself). The glow is a blurred halo
    of `color` reaching about `reach` px past the edge, plus a lit `color`
    rim. While hovered the halo breathes by +-`pulse` of its strength at
    `hz` cycles per second of `t` (seconds). Returns the button's Box."""
    radius = h * 0.28 if radius is None else radius
    g = vb.clamp01(hover)
    if g > 0:
        strength = g * (1 + pulse * math.sin(2 * math.pi * hz * t) * g)
        r, gr, b, _ = (round(v * 255) for v in rgba(color))
        # the blur stays fixed (its mask is made once); only the strength moves
        cv.shadow(x, y, w, h, radius=radius, blur=reach, spread=reach * 0.15,
                  color=(r, gr, b, min(1.0, 0.75 * strength)))
        cv.shadow(x, y, w, h, radius=radius, blur=reach * 0.35, color=(r, gr, b, min(1.0, 0.5 * strength)))
    cv.rect(x, y, w, h, fill, radius=radius)
    cv.outline(x, y, w, h, '#ffffff', width=1.5, radius=radius, alpha=0.08 * (1 - g))
    if g > 0:
        cv.outline(x, y, w, h, color, width=2, radius=radius, alpha=0.85 * g)
    tw, th = vb.text.block_size([label], font)
    vb.text.draw(cv, [label], font, x + (w - tw) / 2, y + (h - th) / 2, ink)
    cv.mark('button', x, y, w, h)
    return vb.Box(x, y, w, h)


def _pointer(cv, x, y, s=1.0):
    pts = [(x + px * s, y + py * s) for px, py in POINTER]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.5))
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill_preserve()
    c.set_source_rgba(0, 0, 0, 1)
    c.set_line_width(2)
    c.stroke()


def draw(n, cv):
    w, h = 270, 76
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    t = n / demo.FPS
    arrive = vb.ease_out_quint(demo.phase(n, 0.4, 1.1))
    hover = vb.ease_out_quint(demo.phase(n, 0.95, 1.5))
    glow_button(cv, x, y, w, h, 'Continue  →', demo.font(28, 700), hover, t=t - 0.95)
    sx, sy = x + w + 150, y + h + 140
    tx, ty = x + w * 0.72, y + h * 0.62
    _pointer(cv, sx + (tx - sx) * arrive, sy + (ty - sy) * arrive)


TECHNIQUE = Technique(
    id='glow-button',
    name='Glow button',
    family='ui',
    group='Buttons',
    aliases=('halo button', 'neon glow', 'glowing button'),
    definition='When the pointer lands on a button, a soft halo of colour swells out from behind it and '
               'its rim lights up, the light gently breathing while the hover lasts.',
    phrasings=('the button lights up with a coloured glow when you hover it',
               'a neon halo appears around the button and softly pulses',
               'mouse over the call to action and it starts glowing'),
    related=('outline-pulse-glow', 'bloom', 'spotlight-hover', 'fresnel-edge-glow', 'drop-target-highlight',
             'border-glow-follow'),
    api=('videobuilder.techniques.ui.glow_button.glow_button',),
    demo=lambda: demo.film(draw),
)

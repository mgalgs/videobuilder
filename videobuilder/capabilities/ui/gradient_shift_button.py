"""Gradient Shift Button: a button whose gradient fill keeps sliding slowly
across its face, and slides further along when the pointer hovers it."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

COLORS = ('#7c80f7', '#3b3f94', '#9c6f1f', '#5d63d8')
CURSOR = [(0, 0), (0, 26), (6.5, 20), (11, 30), (15, 28), (10.5, 18.5), (19, 18.5)]


def gradient_offset(t, hover=0.0, drift=0.12, push=0.6):
    """How far the gradient has slid, in button widths: `drift` widths per
    second of `t`, plus `push` widths scaled by `hover` (0 -> 1)."""
    return drift * t + push * vb.clamp01(hover)


def draw_gradient_button(cv, x, y, w, h, t, hover=0.0, label='Continue', colors=COLORS, radius=None,
                         font=None, ink=demo.INK, drift=0.12, push=0.6):
    """A gradient-filled button with top-left (x, y), at `t` seconds. The
    gradient spans two button widths and mirrors at its ends, so it slides
    forever without a seam; `hover` (0 -> 1) pushes it further along (see
    `gradient_offset`) and lifts the button a touch. Returns its Box."""
    r = h * 0.22 if radius is None else radius
    lift = 3 * vb.clamp01(hover)
    y -= lift
    span = 2 * w
    g = cairo.LinearGradient(0, 0, span, 0)
    for i, c in enumerate(colors):
        g.add_color_stop_rgba(i / (len(colors) - 1), *vb.rgba(c))
    g.set_extend(cairo.EXTEND_REFLECT)
    shift = gradient_offset(t, hover, drift, push) * w
    g.set_matrix(cairo.Matrix(x0=shift - x, y0=0))  # pattern space = user space shifted right by -x + shift
    cv.shadow(x, y, w, h, radius=r, dy=8 + lift, blur=24, color=(0, 0, 0, 0.5))
    with cv.clip(x, y, w, h, radius=r):
        cv.ctx.set_source(g)
        cv.ctx.paint()
    cv.outline(x + 0.5, y + 0.5, w - 1, h - 1, '#ffffff', width=1.5, radius=r, alpha=0.18 + 0.12 * hover)
    f = font or demo.font(round(h * 0.3), 700)
    lw, lh = vb.text.block_size([label], f)
    vb.text.draw(cv, [label], f, x + (w - lw) / 2 - h * 0.15, y + (h - lh) / 2, ink)
    ax, ay = x + w - h * 0.85, y + h / 2
    cv.line(ax - h * 0.18, ay, ax + h * 0.14, ay, ink, width=h * 0.035)
    cv.line(ax + h * 0.02, ay - h * 0.11, ax + h * 0.14, ay, ink, width=h * 0.035)
    cv.line(ax + h * 0.02, ay + h * 0.11, ax + h * 0.14, ay, ink, width=h * 0.035)
    cv.mark('button', x, y, w, h)
    return vb.Box(x, y, w, h)


def _cursor(cv, x, y, s=1.4):
    pts = [(x + px * s, y + py * s) for px, py in CURSOR]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(2)
    c.stroke()


def draw(n, cv):
    t = n / demo.FPS
    w, h = 560, 140
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    hover = vb.ease_in_out_quart(demo.phase(n, 1.2, 2.2))
    draw_gradient_button(cv, x, y, w, h, t, hover=hover, drift=0.25, push=0.8)
    arrive = vb.ease_out_expo(demo.phase(n, 0.7, 1.3))
    sx, sy, tx, ty = x + w + 260, y + h + 260, x + w - 120, y + h * 0.6
    _cursor(cv, sx + (tx - sx) * arrive, sy + (ty - sy) * arrive)


CAPABILITY = Capability(
    id='gradient-shift-button',
    name='Gradient shift button',
    family='ui',
    group='Buttons',
    aliases=('animated gradient button', 'hue drift'),
    definition='A button filled with a gradient that keeps gliding slowly across it, '
               'sliding noticeably further when the pointer rests on it.',
    phrasings=('a button whose colours slowly drift across it and shift more on hover',
               'an animated gradient call-to-action that reacts when you mouse over it',
               'make the button background flow between colours, faster when hovered'),
    related=('animated-gradient-sweep', 'gradient-mesh-drift', 'palette-shift-transition',
             'gradient-sweep-across-text', 'gradient-border-spin', 'scroll-linked-background-shift'),
    api=('videobuilder.capabilities.ui.gradient_shift_button.draw_gradient_button',
         'videobuilder.capabilities.ui.gradient_shift_button.gradient_offset'),
    demo=lambda: demo.film(draw),
)

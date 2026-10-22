"""Light-trail logo reveal: a glowing, slightly bowed beam of light sweeps
across a dark frame dragging a soft haze behind it, and the logo appears
wherever the beam has passed -- white-hot right behind the beam, cooling to
its own colours as the beam moves on."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

LIGHT = '#9fc4ff'


def _edge(hx, cy, half, bow, steps=24):
    """Points down the beam: a curve bulging forward (to +x) at its middle."""
    out = []
    for i in range(steps + 1):
        u = -1 + 2 * i / steps
        out.append((hx - bow * u * u, cy + u * half))
    return out


def _poly(c, pts):
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)


def light_trail_reveal(cv, draw_logo, box, p, x0=None, x1=None, color=LIGHT, height=1.7, bow=None,
                       tail=None, hot=None, fade=0.12):
    """Draw a logo revealed by a travelling beam of light at progress `p`
    (0 -> 1). `draw_logo(cv)` draws the logo; `box` (a vb.Box) is where it
    sits. The beam's middle runs from `x0` to `x1` (default: just outside
    the box on either side), `height` x the box height tall, bowed forward
    by `bow` px. Behind it a haze `tail` px long glows in `color`, and the
    logo shows only behind the beam, lit towards `color`/white over the last
    `hot` px and its own colours further back. Over the last `fade` of `p`
    the beam and haze fade away, leaving the logo clean at 1. Ease `p`
    yourself.

    In a film: `light_trail_reveal(cv, my_logo, logo_box, vb.ease_in_out_quart(t / 1.8))`."""
    p = vb.clamp01(p)
    if p >= 1:
        draw_logo(cv)
        return
    half = box.h * height / 2
    bow = box.h * 0.22 if bow is None else bow
    tail = box.w * 0.6 if tail is None else tail
    hot = box.w * 0.3 if hot is None else hot
    x0 = box.x - bow - box.w * 0.08 if x0 is None else x0
    x1 = box.x + box.w + box.w * 0.08 + bow if x1 is None else x1
    hx, cy = x0 + (x1 - x0) * p, box.y + box.h / 2
    edge = _edge(hx, cy, half, bow)
    strength = vb.clamp01((1 - p) / fade) if fade > 0 else 1.0
    r, g, b, _ = rgba(color)
    c = cv.ctx
    top, bottom = cy - half - box.h, cy + half + box.h

    def behind(dx):  # the region left of the beam, shifted back by dx
        c.new_path()
        c.move_to(-1e4, top)
        c.line_to(edge[0][0] - dx, top)
        _poly(c, [(x - dx, y) for x, y in edge])
        c.line_to(edge[-1][0] - dx, bottom)
        c.line_to(-1e4, bottom)
        c.close_path()

    # The logo, only where the beam has been.
    c.save()
    behind(0)
    c.clip()
    draw_logo(cv)
    c.restore()
    # The freshly lit part: the logo's own pixels washed towards white, hottest at the beam.
    c.save()
    c.push_group()
    draw_logo(cv)
    shape = c.pop_group()
    behind(0)
    c.clip()
    grad = cairo.LinearGradient(hx - hot, 0, hx, 0)
    grad.add_color_stop_rgba(0, r, g, b, 0)
    grad.add_color_stop_rgba(0.6, r, g, b, 0.55)
    grad.add_color_stop_rgba(1, 1, 1, 1, 0.95)
    c.set_source(grad)
    c.mask(shape)
    c.restore()
    if strength <= 0:
        return
    # The beam and its haze, faded out towards the beam's ends.
    c.save()
    c.push_group()
    c.new_path()
    _poly(c, edge)
    _poly(c, [(x - tail, y) for x, y in reversed(edge)])
    c.close_path()
    haze = cairo.LinearGradient(hx - tail, 0, hx, 0)
    haze.add_color_stop_rgba(0, r, g, b, 0)
    haze.add_color_stop_rgba(0.7, r, g, b, 0.2)
    haze.add_color_stop_rgba(1, r, g, b, 0.45)
    c.set_source(haze)
    c.fill()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for width, alpha in ((34, 0.06), (18, 0.12), (8, 0.3)):
        c.new_path()
        _poly(c, edge)
        c.set_source_rgba(r, g, b, alpha)
        c.set_line_width(width)
        c.stroke()
    c.new_path()
    _poly(c, edge)
    c.set_source_rgba(1, 1, 1, 1)
    c.set_line_width(3)
    c.stroke()
    c.pop_group_to_source()
    ends = cairo.LinearGradient(0, cy - half, 0, cy + half)
    for at, a in ((0, 0), (0.25, 1), (0.75, 1), (1, 0)):
        ends.add_color_stop_rgba(at, 0, 0, 0, a * strength)
    c.mask(ends)
    c.restore()
    # The beam's head: a bright point with a halo at its middle.
    halo = cairo.RadialGradient(hx, cy, 0, hx, cy, 40)
    halo.add_color_stop_rgba(0, 1, 1, 1, strength)
    halo.add_color_stop_rgba(0.15, r, g, b, 0.7 * strength)
    halo.add_color_stop_rgba(1, r, g, b, 0)
    c.set_source(halo)
    c.new_path()
    c.arc(hx, cy, 40, 0, 2 * math.pi)
    c.fill()


# The demo's logo: a ring-and-dot mark with a wordmark beside it (plain shapes, not a real logo).
MARK, GAP = 170, 48


def _logo(cv, x, y, f):
    cy = y + MARK / 2
    cv.arc(x + MARK / 2, cy, MARK * 0.4, 0, math.tau, demo.INK, width=MARK * 0.16)
    demo.dot(cv, x + MARK / 2, cy, MARK * 0.14, color=demo.TEAL)
    h = vb.text.block_size(['HALO'], f)[1]
    vb.text.draw(cv, ['HALO'], f, x + MARK + GAP, cy - h / 2, demo.INK)


def draw(n, cv):
    f = demo.font(170, 900)
    w = MARK + GAP + vb.text.block_size(['HALO'], f)[0]
    box = vb.Box((demo.W - w) / 2, (demo.H - MARK) / 2, w, MARK)
    p = demo.phase(n, 0.25, 2.45)
    p = 0.5 - 0.5 * math.cos(math.pi * p)  # ease in and out
    light_trail_reveal(cv, lambda c: _logo(c, box.x, box.y, f), box, p, x0=60, x1=demo.W - 60)
    cv.mark('logo', *box)


CAPABILITY = Capability(
    id='light-trail-logo-reveal',
    name='Light-trail logo reveal',
    family='broadcast',
    group='Bumpers & idents',
    aliases=('light streak ident', 'neon trail reveal', 'light sweep logo reveal', 'light streak logo'),
    definition='A glowing beam of light glides across a dark screen, and the logo is lit up and left '
               'behind wherever the beam has already passed.',
    phrasings=('have a streak of light sweep across and leave our logo glowing behind it',
               'reveal the logo with a beam of light passing over it',
               'a light trail swooshes by and the brand mark appears in its wake'),
    related=('logo-glitch-reveal', 'logo-mask-wipe-reveal', 'logo-build-on-reveal', 'outline-pulse-glow',
             'luma-wipe', 'logo-3d-spin-reveal'),
    api=('videobuilder.capabilities.broadcast.light_trail_logo_reveal.light_trail_reveal',),
    demo=lambda: demo.film(draw),
)

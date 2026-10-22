"""Text reflection shimmer: a word stands on a glossy floor, its upside-down
copy below the baseline sliced into thin bands that waver sideways like
water and fade with depth, while a band of light glides across it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def baseline(font, y):
    """The baseline of a line of `font` drawn with its top at `y`."""
    content, base = vb.text._content(font)
    return y + (vb.text.line_height(font) - content) / 2 + base


def draw_reflection(cv, text, font, x, y, t, color, strength=0.45, depth=None, gap=4, band=6,
                    ripple=6.0, wavelength=38.0, speed=2.2, glint=None, glint_color='#ffffff', glint_width=0.18):
    """Draw one line of `text` from its top-left (x, y), with a mirrored copy
    under its baseline: cut into `band`-px strips, each pushed sideways by up
    to `ripple` px on a wave of `wavelength` px moving at `speed` (rad/s)
    with time `t` (s), and fading from `strength` to nothing over `depth` px
    (default: the text's height). `glint` (0 -> 1, or None) sweeps a soft
    band of `glint_color`, `glint_width` of the text wide, across the
    reflection from left to right. Returns the Box of the upright text."""
    w, h = vb.text.block_size([text], font)
    axis = baseline(font, y) + gap / 2
    depth = depth if depth is not None else (axis - y)
    pad = ripple + 4
    c = cv.ctx

    def strips(ink):
        d = 0.0
        while d < depth:
            k = d / depth  # the wave grows with depth, as a farther surface breaks up more
            dx = ripple * (0.35 + 0.65 * k) * math.sin(d / wavelength * 2 * math.pi - speed * t)
            with cv.clip(x - pad, axis + d, w + 2 * pad, band * 0.72):
                c.save()
                c.translate(dx, 2 * axis)
                c.scale(1, -1)
                vb.text.draw(cv, [text], font, x, y, ink)
                c.restore()
            d += band

    def fade(peak):
        g = cairo.LinearGradient(0, axis, 0, axis + depth)
        g.add_color_stop_rgba(0, 0, 0, 0, peak)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        return g

    c.save()
    c.push_group()
    strips(color)
    c.pop_group_to_source()
    c.mask(fade(strength))
    if glint is not None and 0 < glint < 1:
        span = w * glint_width
        gx = x - span + (w + 2 * span) * glint
        c.push_group()
        strips(glint_color)
        lit = c.pop_group()
        # The light's mask: the sweep across, times the same fall-off down.
        c.push_group()
        c.set_source(fade(1.0))
        c.paint()
        across = cairo.LinearGradient(gx - span, 0, gx + span, 0)
        across.add_color_stop_rgba(0, 0, 0, 0, 0)
        across.add_color_stop_rgba(0.5, 0, 0, 0, 1)
        across.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_operator(cairo.OPERATOR_DEST_IN)
        c.set_source(across)
        c.paint()
        sweep = c.pop_group()
        c.set_operator(cairo.OPERATOR_OVER)
        c.set_source(lit)
        c.mask(sweep)
    c.restore()
    return vb.text.draw(cv, [text], font, x, y, color)


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'HORIZON'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, demo.H / 2 - h * 0.8
    floor = baseline(f, y) + 2
    g = cairo.LinearGradient(0, floor, 0, demo.H)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.05)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    cv.ctx.rectangle(0, floor, demo.W, demo.H - floor)
    cv.ctx.set_source(g)
    cv.ctx.fill()
    box = draw_reflection(cv, text, f, x, y, n / demo.FPS, demo.INK, glint=demo.phase(n, 0.5, 2.6),
                          glint_color=demo.TEAL)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='text-reflection-shimmer',
    name='Text reflection shimmer',
    family='typography',
    group='Depth and 3D',
    aliases=('mirror water text', 'reflected type ripple', 'water reflection text'),
    definition='A word casts an upside-down copy beneath itself that wavers in thin horizontal bands and '
               'fades downward, as if mirrored in still water, with a gleam of light drifting across it.',
    phrasings=('make the title reflect in water underneath, with a little ripple',
               'the text has a mirror image below it that shimmers like a wet floor',
               'a glossy reflection under the headline that wobbles and catches the light'),
    related=('chrome-specular-shimmer', 'chrome-reflection', 'ripple-displacement', 'shine-glint-sweep',
             'skeleton-shimmer', 'gooch-shading'),
    api=('videobuilder.capabilities.typography.text_reflection_shimmer.draw_reflection',
         'videobuilder.capabilities.typography.text_reflection_shimmer.baseline'),
    demo=lambda: demo.film(draw),
)

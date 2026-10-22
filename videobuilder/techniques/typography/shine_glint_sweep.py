"""Shine Glint Sweep: a narrow slanted streak of light crosses the letters,
lighting only the glyphs it passes over, and leaves a brief star-shaped
sparkle as it slips off the last letter."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique

SPARKLE_AT = 0.8  # with a sparkle, the streak's share of the progress


def draw_glint(cv, lines, font, x, y, p, color, shine='#ffffff', band=0.22, tilt=20, strength=0.95,
               sparkle=True, align='left'):
    """Draw `lines` from top-left (x, y) in `color` with a streak of `shine`
    crossing them at progress `p` (0 -> 1): the streak enters at the left
    edge at 0 and is off the right by `SPARKLE_AT` (by 1 without `sparkle`).
    It is clipped to the glyphs, slanted `tilt` degrees from vertical, and
    `band` of the text's width wide. `sparkle` adds a small four-point star
    at the top-right corner that flares and fades as the streak leaves, from
    `SPARKLE_AT - 0.1` to 1. Returns the Box of the text."""
    box = vb.text.draw(cv, lines, font, x, y, color, align=align)
    if not 0 < p < 1:
        return box
    q = p / SPARKLE_AT if sparkle else p
    if q < 1:
        _streak(cv, lines, font, x, y, box, q, shine, band, tilt, strength, align)
    s = vb.clamp01((p - SPARKLE_AT + 0.1) / (1.1 - SPARKLE_AT))
    if sparkle and s > 0:
        star(cv, box.x + box.w - font.size * 0.08, box.y + box.h * 0.22, font.size * 0.45 * math.sin(math.pi * s),
             shine, angle=s * math.pi / 3)
    return box


def _streak(cv, lines, font, x, y, box, p, shine, band, tilt, strength, align):
    c = cv.ctx
    # The streak runs along a direction tilted off horizontal, so its band is slanted.
    a = math.radians(tilt)
    dx, dy = math.cos(a), -math.sin(a)
    proj = [px * dx + py * dy for px in (box.x, box.x + box.w) for py in (box.y, box.y + box.h)]
    half = band * box.w / 2
    start, length = min(proj) - half, max(proj) - min(proj) + 2 * half
    centre = start + p * length
    end = start + length
    g = cairo.LinearGradient(start * dx, start * dy, end * dx, end * dy)
    r, gg, b, _ = rgba(shine)
    for off, al in ((-1, 0), (-0.35, 0.35), (0, 1), (0.35, 0.35), (1, 0)):
        g.add_color_stop_rgba(vb.clamp01((centre + off * half - start) / length), r, gg, b, al * strength)
    c.save()
    c.push_group()
    vb.text.draw(cv, lines, font, x, y, '#ffffff', align=align)  # the glyphs, as a mask
    c.set_operator(cairo.OPERATOR_IN)
    c.set_source(g)
    c.paint()
    c.pop_group_to_source()
    c.paint()
    c.restore()


def star(cv, cx, cy, r, color, angle=0.0, alpha=1.0):
    """A four-point sparkle of radius `r` centred at (cx, cy), with a soft halo."""
    if r <= 0:
        return
    c = cv.ctx
    halo = cairo.RadialGradient(cx, cy, 0, cx, cy, r * 0.8)
    cr, cg, cb, _ = rgba(color)
    halo.add_color_stop_rgba(0, cr, cg, cb, 0.6 * alpha)
    halo.add_color_stop_rgba(1, cr, cg, cb, 0)
    c.save()
    c.set_source(halo)
    c.arc(cx, cy, r * 0.8, 0, 2 * math.pi)
    c.fill()
    c.move_to(cx + r * math.cos(angle), cy + r * math.sin(angle))
    for i in range(1, 8):
        t = angle + i * math.pi / 4
        k = r if i % 2 == 0 else r * 0.14
        c.line_to(cx + k * math.cos(t), cy + k * math.sin(t))
    c.close_path()
    c.set_source_rgba(cr, cg, cb, alpha)
    c.fill()
    c.restore()


GOLD = '#c9a24a'
SWEEP = vb.ease.bezier(0.45, 0, 0.55, 1)  # a gentle in-out, so the streak glides rather than darts


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'PREMIUM'
    w, h = vb.text.block_size([text], f)
    p = SWEEP(demo.phase(n, 0.4, 2.7))
    box = draw_glint(cv, [text], f, (demo.W - w) / 2, (demo.H - h) / 2, p, GOLD, shine='#fff8e0', band=0.2, tilt=24)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='shine-glint-sweep',
    name='Shine glint sweep',
    family='typography',
    group='Surface and light',
    aliases=('glint', 'shine sweep', 'text shine', 'logo shine', 'specular sweep'),
    definition='A thin slanted streak of light travels across a word, brightening only the letters it touches, '
               'and finishes with a small sparkle as it leaves.',
    phrasings=('make a flash of light slide across the title like it is polished metal',
               'give the logo a shiny glint that sweeps over it',
               'a gleam runs across the letters and ends in a little twinkle'),
    related=('sheen-sweep', 'text-reflection-shimmer', 'rim-light', 'spotlight-hover', 'fresnel-edge-glow',
             'gooch-shading'),
    api=('videobuilder.techniques.typography.shine_glint_sweep.draw_glint',
         'videobuilder.techniques.typography.shine_glint_sweep.star'),
    demo=lambda: demo.film(draw),
)

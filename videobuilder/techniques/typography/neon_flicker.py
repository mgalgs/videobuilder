"""Neon flicker: glowing tube lettering stutters on -- dark, a blink, a
half-lit buzz, dark again -- before catching and holding steady."""
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type import kit as tk


def flicker(t, length=1.2, seed=0, slot=(0.03, 0.11)):
    """The tube's brightness 0 -> 1 at `t` seconds after it is switched on:
    0 before, 1 from `length` on, and between a seeded run of short slots
    (each `slot` seconds long, at random) that are dark, half-lit or fully
    lit, lit more often the nearer the end. The same `seed` gives the same
    stutter, frame for frame."""
    if t < 0:
        return 0.0
    if t >= length:
        return 1.0
    r = random.Random(f'neon:{seed}')
    at = 0.0
    while True:
        at += r.uniform(*slot)
        roll = r.random()
        if t < at:
            k = (at / length) ** 0.8         # how far into the stutter: lit more often late on
            if roll < 0.55 * k + 0.12:
                return 1.0
            if roll < 0.75 * k + 0.25:
                return 0.4
            return 0.0


def draw_neon(cv, text, font, x, y, level, color, width=None, off='#2a2d35'):
    """`text` as neon tubing from its top-left (x, y): the letters' outlines
    stroked `width` px (default 1/30 of the font size) with a hot white core,
    and a soft halo of `color` around them, all scaled by `level` (0 unlit,
    1 fully lit, e.g. from `flicker`). The unlit tube shows in `off`, so the
    sign is there even when dark. Returns the Box of the line."""
    width = width or font.size / 30
    w, h = vb.text.block_size([text], font)
    box = vb.Box(x, y, w, h)
    path = tk._outline(text, font)

    def stroke(c, colour, wd, alpha=1.0):
        ctx = c.ctx
        ctx.save()
        ctx.translate(x, y)
        ctx.new_path()
        ctx.append_path(path)
        ctx.set_source_rgba(*vb.canvas.rgba(colour, alpha))
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)              # round joins, like bent glass
        ctx.stroke()
        ctx.restore()

    stroke(cv, off, width)
    if level <= 0:
        return box
    halo = box.pad(-width * 4)
    tk.blurred(cv, halo, font.size * 0.28, lambda c: stroke(c, color, width * 4), alpha=0.75 * level)
    tk.blurred(cv, halo, font.size * 0.06, lambda c: stroke(c, color, width * 2), alpha=level)
    stroke(cv, color, width, alpha=level)
    stroke(cv, tk.mix(color, '#ffffff', 0.7), width * 0.4, alpha=level)
    return box


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'OPEN LATE'
    w, h = vb.text.block_size([text], f)
    level = flicker(n / demo.FPS - 0.4, length=1.6, seed=3)
    box = draw_neon(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, level, '#ff4fa3')
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='neon-flicker',
    name='Neon flicker',
    family='typography',
    group='Glitch and distortion',
    aliases=('neon buzz', 'neon sign flicker', 'tube sign flicker', 'tube glow flicker'),
    definition='Glowing tube-lit lettering blinks on and off in an uneven stutter, sometimes only half lit, '
               'before it catches and stays steadily bright.',
    phrasings=('make the title switch on like an old neon sign',
               'glowing letters that sputter and buzz before they light up for good',
               'a neon sign that flickers a few times and then stays on'),
    related=('outline-pulse-glow', 'fireflies', 'glow-button', 'light-trail-logo-reveal', 'electric-arc',
             'jitter-and-boil-text'),
    api=('videobuilder.techniques.typography.neon_flicker.draw_neon',
         'videobuilder.techniques.typography.neon_flicker.flicker'),
    demo=lambda: demo.film(draw),
)

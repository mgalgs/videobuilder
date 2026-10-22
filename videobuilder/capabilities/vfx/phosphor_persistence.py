"""Phosphor persistence: a bright moving thing leaves a smooth glowing smear
along its path that dies away over a fraction of a second, the way a CRT's
phosphor keeps glowing after the beam has moved on."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def phosphor_persistence(cv, draw_at, t, decay=0.2, span=4.0, samples=120, gain=0.09):
    """Draw the afterglow of a moving subject, then the subject itself, added
    as light. `draw_at(cv, tk, strength)` draws the subject as it was at time
    `tk` (seconds) at brightness `strength` (1 for the live beam). The glow
    looks back `span * decay` seconds in `samples` even steps, each one
    `gain * exp(-age / decay)` bright, so the steps blend into one continuous
    smear that fades exponentially with age and closes up when the subject
    stops. Everything is drawn with an additive operator, so overlapping
    glow brightens instead of covering."""
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    back = span * decay
    for i in range(samples, 0, -1):
        age = back * i / samples
        draw_at(cv, t - age, gain * math.exp(-age / decay))
    draw_at(cv, t, 1.0)
    c.restore()


def beam(cv, cx, cy, strength, r=13, color='#7dffb0', core='#f2fff6', halo=3.2):
    """A phosphor spot at (cx, cy): a soft halo `halo * r` wide in `color`
    scaled by `strength`, and a hot `core` of radius `r` scaled by
    `strength ** 2`, so the live spot burns white and its afterglow is colour. Meant as the
    `draw_at` subject of `phosphor_persistence`."""
    hr, hg, hb, _ = vb.rgba(color)
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r * halo)
    g.add_color_stop_rgba(0, hr, hg, hb, min(1.0, 0.9 * strength))
    g.add_color_stop_rgba(0.35, hr, hg, hb, min(1.0, 0.35 * strength))
    g.add_color_stop_rgba(1, hr, hg, hb, 0)
    cv.ctx.rectangle(cx - r * halo, cy - r * halo, 2 * r * halo, 2 * r * halo)
    cv.ctx.set_source(g)
    cv.ctx.fill()
    cr, cg, cb, _ = vb.rgba(core)
    strength *= strength
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, cr, cg, cb, min(1.0, strength))
    g.add_color_stop_rgba(0.7, cr, cg, cb, min(1.0, 0.8 * strength))
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    cv.ctx.rectangle(cx - r, cy - r, 2 * r, 2 * r)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def _path(t):
    # An oscilloscope-style figure: the beam sweeps a Lissajous loop at an even pace.
    s = 0.55 * t
    return (demo.W / 2 + 330 * math.sin(2 * math.pi * 0.9 * s + 0.6),
            demo.H / 2 + 175 * math.sin(2 * math.pi * 1.35 * s))


def draw(n, cv):
    cv.fill('#060a08')
    for y in range(0, demo.H, 4):  # faint scanlines so it reads as a screen
        cv.rect(0, y, demo.W, 1.5, '#0d1611')
    phosphor_persistence(cv, lambda c, tk, k: beam(c, *_path(tk), k), n / demo.FPS)
    x, y = _path(n / demo.FPS)
    cv.mark('beam', x - 13, y - 13, 26, 26)


CAPABILITY = Capability(
    id='phosphor-persistence',
    name='Phosphor persistence',
    family='vfx',
    group='CRT & display',
    aliases=('phosphor trails', 'phosphor afterglow', 'phosphor bloom', 'CRT persistence'),
    definition='A bright moving spot leaves a soft glowing streak behind it that fades out within moments, '
               'like an old screen still glowing where the beam just passed.',
    phrasings=('make the dot leave a glowing trail that fades like an old oscilloscope',
               'bright things should smear and linger a moment like on a CRT',
               'a fading afterglow behind anything that moves fast'),
    related=('bloom', 'fireflies', 'light-trail-logo-reveal', 'particle-trail', 'thin-film-iridescence',
             'light-painting'),
    api=('videobuilder.capabilities.vfx.phosphor_persistence.phosphor_persistence',
         'videobuilder.capabilities.vfx.phosphor_persistence.beam'),
    demo=lambda: demo.film(draw),
)

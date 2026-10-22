"""Sine wave text: each letter rides up and down on a sine curve laid along
the line, and the curve slides sideways over time so a wave rolls through
the word."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def wave(text, font, t, amplitude=None, wavelength=None, period=1.5, tilt=0.4):
    """Each character of `text` at time `t` seconds as `(char, x, dy, angle)`:
    `x` its left edge from the line's start, `dy` its vertical offset in px
    (down is positive) and `angle` its turn in radians. The curve is
    `amplitude` high (default a quarter of the font size) and `wavelength`
    long (default four font sizes), measured along the line so letters of
    any width sit on it; it travels one wavelength left-to-right every
    `period` seconds. `tilt` 1 turns each letter fully to the curve's slope,
    0 keeps it upright; the default 0.4 gives a lean."""
    amplitude = font.size / 4 if amplitude is None else amplitude
    wavelength = font.size * 4 if wavelength is None else wavelength
    k, w = 2 * math.pi / wavelength, 2 * math.pi / period
    out, x = [], 0.0
    for ch in text:
        adv = vb.text.measure(ch, font)
        u = k * (x + adv / 2) - w * t
        out.append((ch, x, -amplitude * math.sin(u), -tilt * math.atan(amplitude * k * math.cos(u))))
        x += adv
    return out


def draw_wave_text(cv, text, font, x, y, t, color, alpha=1.0, **kw):
    """Draw `text` waving at time `t` seconds from its top-left (x, y), each
    letter turned about its own centre. `kw` goes to `wave` (`amplitude`,
    `wavelength`, `period`, `tilt`). Returns the Box of the line at rest."""
    w, h = vb.text.block_size([text], font)
    ctx = cv.ctx
    for ch, cx, dy, angle in wave(text, font, t, **kw):
        if ch.isspace():
            continue
        half = vb.text.measure(ch, font) / 2
        ctx.save()
        ctx.translate(x + cx + half, y + h / 2 + dy)
        ctx.rotate(angle)
        vb.text.draw(cv, [ch], font, -half, -h / 2, color, alpha=alpha)
        ctx.restore()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(96, 800)
    text = 'WAVY TEXT'
    w, h = vb.text.block_size([text], f)
    box = draw_wave_text(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, n / demo.FPS, demo.INK)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='sine-wave-text',
    name='Sine wave text',
    family='typography',
    group='Wave and motion',
    aliases=('wave text', 'wavy text', 'bouncing wave letters'),
    definition='The letters of a word bob up and down along a sine curve that keeps sliding sideways, '
               'so a smooth wave rolls through the line.',
    phrasings=('make the title ripple like it is floating on water',
               'the letters rise and fall one after another in a rolling wave',
               'wavy text that undulates across the word'),
    related=('sine-wave-distortion', 'wave-stagger', 'oscillation', 'wave-deformer', 'ripple-displacement',
             'text-on-a-path'),
    api=('videobuilder.techniques.typography.sine_wave_text.draw_wave_text',
         'videobuilder.techniques.typography.sine_wave_text.wave'),
    demo=lambda: demo.film(draw),
)

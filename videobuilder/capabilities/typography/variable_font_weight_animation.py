"""Variable-font weight animation: the letters themselves thicken and thin
by sliding a variable font's weight (`wght`) axis, smoothly rather than
jumping between a few fixed cuts. The weight can move the whole word at once
or roll across it letter by letter as a wave.

`vb.Font` already takes any value on the axis (`weight=`); what this adds is
laying out a line whose letters each have their own weight, so it stays
centred while their widths change, and the wave that drives them."""
import math

import videobuilder as vb

from ... import fonts
from .. import _demo as demo
from ..schema import Technique

THIN, BLACK = 100, 900


def weight_wave(count, p, lo=THIN, hi=BLACK, width=1.6):
    """Per-letter weights for `count` letters as a swell rolls across them at
    progress `p` (0 -> 1): at 0 the crest sits `width` letters before the
    first, at 1 the same distance past the last, so every letter rises from
    `lo` to `hi` and falls back in turn. `width` is the crest's half-width in
    letters."""
    centre = -width + vb.clamp01(p) * (count - 1 + 2 * width)
    out = []
    for i in range(count):
        d = abs(i - centre) / width
        k = 0.5 + 0.5 * math.cos(math.pi * d) if d < 1 else 0.0
        out.append(round(lo + (hi - lo) * k))
    return out


def draw_weighted(cv, text, font, weights, cx, y, color, alpha=1.0):
    """Draw `text` with each character at its own weight from `weights` (one
    per character; `font` gives family, size and the rest), as one line
    centred on `cx` with its top at `y`. Each letter takes its true advance
    at its current weight, so the line breathes but never overlaps. Returns
    the line's Box."""
    faces = [vb.Font(font.family, font.size, weight=w, tracking=font.tracking, style=font.style)
             for w in weights]
    advances = [vb.text.measure(ch, f) for ch, f in zip(text, faces)]
    x = cx - sum(advances) / 2
    left = x
    for ch, f, adv in zip(text, faces, advances):
        if not ch.isspace():
            vb.text.draw(cv, [ch], f, x, y, color, alpha=alpha)
        x += adv
    return vb.Box(left, y, x - left, vb.text.line_height(font))


_family = None


def _variable_family():
    """The bundled variable sans (Inter), registered once; the kit's sans if
    it can't be loaded, which still animates but may snap between cuts."""
    global _family
    if _family is None:
        _family = demo.font(10).family
        path = fonts.path('inter')
        if path:
            try:
                vb.text.register(path)
                _family = fonts.get('inter')['family']
            except RuntimeError:
                pass
    return _family


def draw(n, cv):
    family = _variable_family()
    text = 'Variable'
    size = 150
    font = vb.Font(family, size)
    y = demo.H / 2 - vb.text.line_height(font) / 2 - 30
    # First the whole word swells thin -> black and back, then a wave rolls through it.
    whole = demo.phase(n, 0.2, 1.4)
    if whole < 1:
        w = round(THIN + (BLACK - THIN) * math.sin(math.pi * whole) ** 2)
        weights = [w] * len(text)
    else:
        weights = weight_wave(len(text), demo.phase(n, 1.45, 2.85))
    box = draw_weighted(cv, text, font, weights, demo.W / 2, y, demo.INK)
    cv.mark('text', *box)

    # A small readout of the axis: a track from 100 to 900 with a tick per letter.
    tx, ty, tw = demo.W / 2 - 220, box.y + box.h + 40, 440
    cv.line(tx, ty, tx + tw, ty, demo.LINE, width=3)
    for w in sorted(set(weights)):
        demo.dot(cv, tx + tw * (w - THIN) / (BLACK - THIN), ty, r=7, color=demo.ACCENT)
    label = demo.mono(20, 500)
    vb.text.draw(cv, [f'wght {THIN}'], label, tx - 130, ty - 13, demo.MUTED)
    vb.text.draw(cv, [f'{BLACK}'], label, tx + tw + 16, ty - 13, demo.MUTED)


TECHNIQUE = Technique(
    id='variable-font-weight-animation',
    name='Variable-font weight animation',
    family='typography',
    group='Variable font',
    aliases=('weight animation', 'variable font animation', 'wght axis animation', 'font weight morph'),
    definition='Letters grow bolder or lighter in one smooth motion by sliding a variable font along its '
               'weight axis, for the whole word at once or rippling through it letter by letter.',
    phrasings=('make the title go from hairline thin to really bold, smoothly',
               'a wave of boldness that rolls across the word',
               'animate the font weight so the letters swell and slim down'),
    related=('text-to-shape-morph', 'chart-type-morph', 'shape-morph-loader', 'arc-bend-morph',
             'twirl-warp-text', 'julia-set-morph'),
    api=('videobuilder.techniques.typography.variable_font_weight_animation.draw_weighted',
         'videobuilder.techniques.typography.variable_font_weight_animation.weight_wave',
         'videobuilder.Font'),
    demo=lambda: demo.film(draw),
)

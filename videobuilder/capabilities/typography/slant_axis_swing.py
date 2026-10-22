"""Slant Axis Swing: a line of type leans from upright into an oblique and
back, the way a variable font's slant axis moves, with the letters sheared
about their baseline so the word stays planted where it stands."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def slant_swing(p, degrees=12.0, hold=0.3):
    """The slant, in degrees, at progress `p` (0 -> 1) of one swing: eased
    from upright to `degrees`, held there for `hold` of the time, then eased
    back upright. Positive leans the tops of the letters right."""
    p = vb.clamp01(p)
    move = (1 - hold) / 2
    if p < move:
        t = p / move
    elif p < move + hold:
        t = 1.0
    else:
        t = 1 - (p - move - hold) / move
    t = vb.clamp01(t)
    return degrees * (3 * t * t - 2 * t * t * t)   # smoothstep: settles softly at both ends


def draw_slanted(cv, text, font, cx, cy, degrees, color, alpha=1.0):
    """Draw `text` on one line centred at (cx, cy), sheared `degrees` off
    upright about its baseline (positive leans right, like an italic), so the
    baseline stays put and only the tops of the letters travel. Returns the
    Box of the upright line."""
    w, h = vb.text.block_size([text], font)
    x, y = cx - w / 2, cy - h / 2
    baseline = y + vb.text._content(font)[1] + (vb.text.line_height(font) - vb.text._content(font)[0]) / 2
    c = cv.ctx
    c.save()
    c.translate(cx, baseline)
    c.transform(cairo.Matrix(1, 0, -math.tan(math.radians(degrees)), 1, 0, 0))   # x -= tan * y; y < 0 above
    c.translate(-cx, -baseline)
    vb.text.draw(cv, [text], font, x, y, color, alpha=alpha)
    c.restore()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 850)
    deg = slant_swing(demo.phase(n, 0.3, 2.7), degrees=14)
    box = draw_slanted(cv, 'MOTION', f, demo.W / 2, demo.H / 2 - 20, deg, demo.INK)
    cv.mark('text', *box)
    demo.word(cv, f'slnt  {0.0 - deg:5.1f}°', demo.W / 2, demo.H / 2 + 130, size=30, color=demo.MUTED,
              font=demo.mono(30, 500))


TECHNIQUE = Technique(
    id='slant-axis-swing',
    name='Slant axis swing',
    family='typography',
    group='Variable font',
    aliases=('italic axis morph', 'oblique animation', 'slant morph'),
    definition='A word tips smoothly from upright type into a leaning oblique and then straightens up again, '
               'its baseline staying fixed while the letter tops travel sideways.',
    phrasings=('make the title lean into italics and then stand back up',
               'animate the text going from upright to slanted and back',
               'the letters tilt forward like italics for a moment'),
    related=('arc-bend-morph', 'character-rotate-in', 'chart-type-morph', 'angled-lower-third', 'dutch-angle',
             'text-to-shape-morph'),
    api=('videobuilder.techniques.typography.slant_axis_swing.draw_slanted',
         'videobuilder.techniques.typography.slant_axis_swing.slant_swing'),
    demo=lambda: demo.film(draw),
)

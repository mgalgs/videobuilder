"""Chrome Specular Shimmer: the letters are polished metal -- a bright sky,
a hard dark horizon, a warm ground reflected in them -- and as the light
turns, the reflection slides and tilts and a white glint runs across."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SKY = ('#ffffff', '#c4d2e4', '#6f819c')       # top of the letter down to the horizon
GROUND = ('#15171d', '#4a423b', '#e2dcd2')    # just under the horizon down to the foot


def chrome_pattern(x, y, w, h, light, horizon=0.5, tilt=0.14, travel=0.16):
    """A cairo gradient that reads as chrome over the box (x, y, w, h) of a
    line of text, with the light at `light` (-1 -> 1, left to right): a
    bright sky, a hard dark horizon, a warm ground with a thin bright band
    reflected in it. The horizon sits at `horizon` of the glyphs' height,
    rises and falls by `travel` and leans by `tilt` radians as the light
    moves, so animating `light` makes the surface shift like turning metal."""
    a = math.pi / 2 + tilt * light                      # gradient axis: near vertical, leaning with the light
    cx, cy = x + w / 2, y + h / 2
    half = h * 0.32                                     # about the cap height of a line box
    dx, dy = math.cos(a) * half, math.sin(a) * half
    g = cairo.LinearGradient(cx - dx, cy - dy, cx + dx, cy + dy)
    hz = min(0.8, max(0.2, horizon - travel * light))
    ground = 1 - hz
    stops = ((0.0, SKY[0]), (hz * 0.5, SKY[1]), (hz - 0.003, SKY[2]),
             (hz + 0.003, GROUND[0]), (hz + ground * 0.3, GROUND[1]),
             (hz + ground * 0.45, GROUND[2]), (hz + ground * 0.55, GROUND[1]), (1.0, GROUND[2]))
    for t, c in stops:
        g.add_color_stop_rgba(t, *vb.rgba(c))
    return g


def glint_pattern(x, y, w, h, p, width=0.12, angle=0.5, strength=0.9):
    """A soft white diagonal band at progress `p` (0 -> 1, left to right
    across the box), leaning by `angle` radians: the specular highlight."""
    lean = math.tan(angle) * h
    x0 = x - lean - w * width + (w + lean + 2 * w * width) * p
    g = cairo.LinearGradient(x0 - w * width, y + h, x0 + w * width + lean, y)
    g.add_color_stop_rgba(0.0, 1, 1, 1, 0)
    g.add_color_stop_rgba(0.5, 1, 1, 1, strength)
    g.add_color_stop_rgba(1.0, 1, 1, 1, 0)
    return g


def draw_chrome_text(cv, text, font, x, y, light, glint=None, edge='#0b0c10', alpha=1.0):
    """Draw `text` (a line, or lines) from its top-left (x, y) as chrome lit
    from `light` (-1 -> 1; animate it to make the reflection shimmer).
    `glint`, if given, is the 0 -> 1 progress of a specular streak across
    the line. `edge` is a thin dark rim under the face so it reads on any
    background. Returns the Box the text takes up."""
    lines = [text] if isinstance(text, str) else list(text)
    ctx = cv.ctx
    w, h = vb.text.block_size(lines, font)
    rim = max(1.0, font.size * 0.025)
    for ox, oy in ((-rim, 0), (rim, 0), (0, -rim), (0, rim), (rim, rim)):
        vb.text.draw(cv, lines, font, x + ox, y + oy, edge, alpha=alpha)
    ctx.push_group()
    box = vb.text.draw(cv, lines, font, x, y, '#ffffff', alpha=alpha)
    mask = ctx.pop_group()
    ctx.push_group()
    ctx.set_source(chrome_pattern(x, y, w, h, light))
    ctx.paint()
    if glint is not None and 0 < glint < 1:
        ctx.set_source(glint_pattern(x, y, w, h, glint))
        ctx.paint()
    ctx.pop_group_to_source()
    ctx.mask(mask)
    return box


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'CHROME'
    w, h = vb.text.block_size([text], f)
    t = n / demo.FPS
    light = math.sin(2 * math.pi * (t / demo.SECONDS) - math.pi / 2)  # swings -1 -> 1 -> -1
    box = draw_chrome_text(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, light,
                           glint=demo.phase(n, 0.6, 1.8))
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='chrome-specular-shimmer',
    name='Chrome specular shimmer',
    family='typography',
    group='Surface and light',
    aliases=('metallic letter shine', 'environment reflection text', 'chrome text', 'polished metal type'),
    definition='Letters look like mirror-polished metal, with a reflected sky and horizon that slide '
               'and tilt across them as the light turns, and a bright glint that flashes over the surface.',
    phrasings=('make the title look like shiny chrome with the light moving over it',
               'polished metal letters that catch the light',
               'give the logo text a glossy silver reflection that shifts'),
    related=('chrome-reflection', 'text-reflection-shimmer', 'y2k-chrome', 'gooch-shading', 'sheen-sweep',
             'thin-film-iridescence'),
    api=('videobuilder.techniques.typography.chrome_specular_shimmer.draw_chrome_text',
         'videobuilder.techniques.typography.chrome_specular_shimmer.chrome_pattern',
         'videobuilder.techniques.typography.chrome_specular_shimmer.glint_pattern'),
    demo=lambda: demo.film(draw),
)

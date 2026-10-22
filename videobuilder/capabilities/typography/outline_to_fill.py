"""Outline-to-fill: a word starts as hollow strokes, then solid colour rises
up inside the letters from the baseline while the stroke fades away."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba
from ...type import kit as type_kit


def draw_outline_to_fill(cv, text, font, x, y, p, color, stroke=3.0, outline=None, fade_from=0.6):
    """Draw one line of `text` from its top-left (x, y) at progress `p` (0 -> 1):
    at 0 only the letters' outlines, `stroke` px wide; as `p` grows a solid fill
    rises inside them from the bottom of the line to the top, full at 1. The
    outline (in `outline`, default `color`) fades out over the last stretch,
    from `fade_from` to 1, so the end is the plain filled word. Ease `p`
    yourself. Returns the Box of the line, as `text.draw` would."""
    p = vb.clamp01(p)
    w, h = vb.text.block_size([text], font)
    path = type_kit._outline(text, font)
    ctx = cv.ctx
    if p > 0:
        level = y + h * (1 - p)
        with cv.clip(x - stroke, level, w + 2 * stroke, y + h - level + stroke):
            ctx.save()
            ctx.translate(x, y)
            ctx.new_path()
            ctx.append_path(path)
            ctx.set_source_rgba(*rgba(color))
            ctx.fill()
            ctx.restore()
    fade = 1 - vb.clamp01((p - fade_from) / (1 - fade_from)) if fade_from < 1 else 1.0
    if fade > 0:
        ctx.save()
        ctx.translate(x, y)
        ctx.new_path()
        ctx.append_path(path)
        ctx.set_line_width(stroke)
        ctx.set_line_join(1)  # cairo.LINE_JOIN_ROUND
        ctx.set_source_rgba(*rgba(outline or color, fade))
        ctx.stroke()
        ctx.restore()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    p = vb.bezier(0.45, 0, 0.55, 1)(demo.phase(n, 0.5, 2.5))
    box = draw_outline_to_fill(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, p, demo.INK, stroke=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='outline-to-fill',
    name='Outline-to-fill',
    family='typography',
    group='Stroke and outline',
    aliases=('outline fill transition', 'stroke to solid', 'outline to solid text'),
    definition='A word shown only as thin hollow outlines fills up with solid colour from the bottom, '
               'and the outline melts away once the letters are full.',
    phrasings=('the title starts as just an outline and then fills in solid',
               'hollow letters that fill up with colour',
               'stroke-only text that turns into solid text'),
    related=('icon-line-to-fill', 'letter-morph', 'ink-outline', 'color-fill-rise', 'shape-fill-sweep',
             'line-draw-logo-reveal'),
    api=('videobuilder.capabilities.typography.outline_to_fill.draw_outline_to_fill',),
    demo=lambda: demo.film(draw),
)

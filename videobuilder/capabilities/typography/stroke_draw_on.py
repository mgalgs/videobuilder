"""Stroke Draw-on: a thin pen line runs round the contours of each letter,
one letter after the next, and once the outlines are closed the solid fill
fades up inside them."""
from functools import lru_cache

import cairo
from gi.repository import PangoCairo

import videobuilder as vb

from ... import paths, text
from .. import _demo as demo
from ..schema import Capability


@lru_cache(maxsize=256)
def letter_contours(line, font):
    """Every glyph contour of `line` drawn from (0, 0) as `text.draw` would,
    grouped per character: a tuple with one entry per character, each a tuple
    of closed point lists (film px). Spaces have no contours."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    content, _ = text._content(font)
    top = (text.line_height(font) - content) / 2
    out = []
    for i, ch in enumerate(line):
        ctx.new_path()
        ctx.move_to(text.measure(line[:i], font), top)
        PangoCairo.layout_path(ctx, text._layout(ctx, ch, font))
        contours, cur = [], []
        for kind, pt in ctx.copy_path_flat():
            if kind == cairo.PATH_MOVE_TO:
                if len(cur) > 2:
                    contours.append(tuple(cur))
                cur = [pt]
            elif kind == cairo.PATH_LINE_TO:
                cur.append(pt)
            elif kind == cairo.PATH_CLOSE_PATH:
                if len(cur) > 2:
                    contours.append(tuple(cur))
                cur = []
        if len(cur) > 2:
            contours.append(tuple(cur))
        out.append(tuple(contours))
    return tuple(out)


def draw_stroke_on(cv, line, font, x, y, p, color, fill=None, width=2.5, stagger=0.5, fill_from=0.7,
                   ease=vb.ease_in_out_quart, alpha=1.0):
    """Draw `line` from its top-left (x, y) at progress `p` (0 -> 1): each
    letter's outline is traced in `color`, every contour of a letter at once
    from its own start point, the letters starting one after another
    (`stagger` 0 = all together, 1 = strictly one at a time) and all closed
    by `fill_from`. From `fill_from` to 1 the solid fill (`fill`, default
    `color`) fades up inside the strokes. Returns the Box of the line."""
    p = vb.clamp01(p)
    groups = letter_contours(line, font)
    k = len(groups)
    trace = vb.clamp01(p / fill_from) if fill_from > 0 else 1.0
    each = 1.0 / (1 + (k - 1) * stagger) if k else 1.0       # one letter's share of the trace
    fade = vb.clamp01((p - fill_from) / (1 - fill_from)) if fill_from < 1 else float(p >= 1)
    with cv.layer(opacity=alpha, dx=x, dy=y):
        if fade > 0:
            text.draw(cv, [line], font, 0, 0, fill or color, alpha=fade)
        for i, contours in enumerate(groups):
            q = ease(vb.clamp01((trace - i * each * stagger) / each))
            if q <= 0:
                continue
            for c in contours:
                paths.draw(cv, paths.reveal(c, q, closed=True), color, width=width)
    w, h = text.block_size([line], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(190, 800)
    line = 'OUTLINE'
    w, h = text.block_size([line], f)
    box = draw_stroke_on(cv, line, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.2, 2.6),
                         demo.ACCENT, fill=demo.INK, width=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='stroke-draw-on',
    name='Stroke draw-on',
    family='typography',
    group='Stroke and outline',
    aliases=('outline trace', 'line draw-on', 'trim path reveal', 'stroke reveal', 'stroke-dashoffset text',
             'line-draw lettering'),
    definition='A pen line travels around the edges of every letter until each outline is closed, '
               'and only then does the solid colour fill in.',
    phrasings=('draw the outline of the title on first, then fill it in',
               'the letters get sketched as thin lines before they turn solid',
               'trace the word like a pen going round each letter'),
    related=('line-draw-logo-reveal', 'ink-outline', 'stroke-draw-logo-loader', 'line-chart-draw-on',
             'map-route-draw', 'icon-line-to-fill'),
    api=('videobuilder.capabilities.typography.stroke_draw_on.draw_stroke_on',
         'videobuilder.capabilities.typography.stroke_draw_on.letter_contours',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

"""Color Fill Rise: the letters sit as a pale ghost, then a solid colour
floods up through them from the baseline until the whole word is filled."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ink_span(lines, font):
    """(top, bottom) of the lettering's ink in `lines`, px below the block's
    top as `vb.text.draw` lays it out, so a fill can start where the
    letters start rather than at the line box's padding."""
    lh, (content, _) = vb.text.line_height(font), vb.text._content(font)
    pad = (lh - content) / 2
    top, bottom = float('inf'), float('-inf')
    for i, t in enumerate(lines):
        ink = vb.text._layout(vb.text._scratch, t, font).get_extents()[0]
        top = min(top, i * lh + pad + ink.y / vb.text.S)
        bottom = max(bottom, i * lh + pad + (ink.y + ink.height) / vb.text.S)
    return top, bottom


def draw_fill_rise(cv, lines, font, x, y, p, color, empty=None, empty_alpha=0.25, align='left', width=None):
    """Draw `lines` from their top-left (x, y) with `color` risen to progress
    `p` (0 -> 1): below a flat level the text is `color`, above it `empty`
    (default: `color`) at `empty_alpha`. The level climbs the letters' ink,
    so at 0 nothing is filled and at 1 all of it. `align` and `width` go to
    `vb.text.draw`. Returns the text's Box."""
    w, h = vb.text.block_size(lines, font)
    box = vb.Box(x, y, width or w, h)
    p = vb.clamp01(p)
    top, bottom = ink_span(lines, font)
    level = y + bottom - (bottom - top) * p
    x0, x1, y0, y1 = x - h, x + box.w + h, y - h, y + 2 * h  # generous: glyphs can overhang the line box
    if p < 1 and empty_alpha > 0:
        with cv.clip(x0, y0, x1 - x0, level - y0):
            vb.text.draw(cv, lines, font, x, y, empty or color, align=align, width=width, alpha=empty_alpha)
    if p > 0:
        with cv.clip(x0, level, x1 - x0, y1 - level):
            vb.text.draw(cv, lines, font, x, y, color, align=align, width=width)
    return box


RISE = vb.ease.bezier(0.25, 0.1, 0.75, 0.9)  # a near-steady level, softened only at the ends


def draw(n, cv):
    f = demo.font(260, 900)
    text = ['FILL']
    w, h = vb.text.block_size(text, f)
    p = RISE(demo.phase(n, 0.3, 2.9))  # ~70% risen at the 2.1s poster, full by 2.9s
    box = draw_fill_rise(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, p, demo.ACCENT, empty=demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='color-fill-rise',
    name='Color fill rise',
    family='typography',
    group='Masking and clipping',
    aliases=('text fill up', 'bottom-up color fill', 'fill reveal'),
    definition='A solid colour climbs up through faint lettering from bottom to top behind a straight level, '
               'until every letter is filled in.',
    phrasings=('make the title fill up with colour from the bottom',
               'the word starts empty and colour rises inside it like a level going up',
               'paint the text in from the bottom to the top'),
    related=('liquid-fill-level', 'hue-cycle-fill', 'outline-to-fill', 'liquid-melt', 'choropleth-fill',
             'beveled-3d-text'),
    api=('videobuilder.capabilities.typography.color_fill_rise.draw_fill_rise',
         'videobuilder.capabilities.typography.color_fill_rise.ink_span'),
    demo=lambda: demo.film(draw),
)

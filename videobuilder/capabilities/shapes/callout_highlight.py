"""Callout highlight: the frame dims around one region, a bright frame closes
in on that region, and a small label tag pops up beside it to say why it
matters."""
import cairo

import videobuilder as vb
from videobuilder.canvas import _rounded

from .. import _demo as demo
from ..schema import Capability


def callout_highlight(cv, box, p, label=None, color=demo.ACCENT, dim=0.62, pad=14, radius=16,
                      font=None, ink=demo.INK, side='above'):
    """Highlight `box` (x, y, w, h) at progress `p` (0 -> 1), drawn over what
    is already on `cv`. Over the first half the rest of the frame dims to
    `dim` and the hole in the dim closes from the whole frame onto `box`
    (grown by `pad`); an outline in `color` lands on it. Over the second half
    `label`, if given, springs up in a tag `side` ('above' or 'below') the
    box. Returns the highlighted Box."""
    x, y, w, h = box
    ring = vb.Box(x - pad, y - pad, w + 2 * pad, h + 2 * pad)
    a = vb.ease_out_quint(vb.clamp01(p / 0.5))
    if a <= 0:
        return ring
    # the hole: from the whole frame onto the ring
    hx, hy = ring.x * a, ring.y * a
    hw = cv.width + (ring.w - cv.width) * a
    hh = cv.height + (ring.h - cv.height) * a
    ctx = cv.ctx
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.new_path()
    ctx.rectangle(0, 0, cv.width, cv.height)
    _rounded(ctx, hx, hy, hw, hh, radius * a)
    ctx.set_source_rgba(0.03, 0.035, 0.05, dim * a)
    ctx.fill()
    ctx.restore()
    cv.outline(hx, hy, hw, hh, color, width=4, radius=radius * a, alpha=a)
    cv.mark('highlight', *ring)

    if label:
        s = vb.ease_out_back(vb.clamp01((p - 0.5) / 0.35))
        if s > 0:
            f = font or demo.font(30, 800)
            tw, th = vb.text.block_size([label], f)
            tag_w, tag_h = tw + 36, th + 20
            tx = ring.x
            ty = ring.y - tag_h - 18 if side == 'above' else ring.bottom + 18
            with cv.layer(opacity=vb.clamp01(s * 2), dy=(12 if side == 'above' else -12) * (1 - s)):
                cv.rect(tx, ty, tag_w, tag_h, color, radius=tag_h / 2)
                stem_x = tx + 34
                stem = (ty + tag_h, ring.y) if side == 'above' else (ring.bottom, ty)
                cv.line(stem_x, stem[0], stem_x, stem[1], color, width=4)
                vb.text.draw(cv, [label], f, tx + 18, ty + 10, ink)
            cv.mark('label', tx, ty, tag_w, tag_h)
    return ring



def draw(n, cv):
    xs = (demo.W / 2 - 340, demo.W / 2, demo.W / 2 + 340)
    cy = demo.H / 2 + 50
    for x in xs:
        demo.card(cv, x, cy, w=280, h=180, color=demo.TEAL)
    callout_highlight(cv, (xs[1] - 140, cy - 90, 280, 180), demo.phase(n, 0.5, 2.1), label='New this week')


CAPABILITY = Capability(
    id='callout-highlight',
    name='Callout highlight',
    family='shapes',
    group='Explainer & infographic',
    aliases=('spotlight callout', 'focus highlight', 'highlight box'),
    definition='Everything but one area darkens, a bright frame closes in around that area, '
               'and a small tag appears beside it naming what to look at.',
    phrasings=('dim the rest of the screen and box the part I want people to notice',
               'spotlight one card with an outline and a little label',
               'draw attention to this section with a highlight and a note'),
    related=('callout-line-with-label', 'highlight-circle-draw', 'highlighter-swipe',
             'dimension-line-annotation', 'word-by-word-emphasis', 'focus-ring-draw'),
    api=('videobuilder.capabilities.shapes.callout_highlight.callout_highlight',),
    demo=lambda: demo.film(draw),
)

"""Accordion Fold Text: a word sits on a strip pleated into vertical
panels like a paper fan; the pleats open out until the strip lies flat."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw_accordion_fold(cv, draw_flat, x, y, w, h, p, pleats=8, max_angle=80, depth=0.3, slices=6,
                        shade=0.55):
    """Draw whatever `draw_flat(canvas)` draws inside the box (x, y, w, h),
    pleated into `pleats` vertical panels folded at `max_angle` degrees when
    `p` is 0 and lying flat at 1. The folded strip stays centred on the box;
    its width shrinks with the cosine of the fold, the valleys between
    panels shrink by up to `depth` of the height for perspective, and the
    panels facing away darken by up to `shade`. Each panel is drawn in
    `slices` columns, so the perspective is smooth. `draw_flat` draws in
    frame coordinates onto the (offscreen) canvas it is given. Returns the
    Box the folded strip takes up."""
    p = vb.clamp01(p)
    theta = math.radians(min(max_angle, 89) * (1 - p))
    cos, sin = math.cos(theta), math.sin(theta)
    sw = w / pleats                     # one panel's flat width
    left = x + (w - w * cos) / 2        # the folded strip, centred on the box
    cy = y + h / 2
    c = cv.ctx
    pad = 0.6 / cv.scale                # overlap the columns a hair so no seams show
    # Text laid out under a squashed transform keeps its own advance widths, so
    # draw the flat strip once, offscreen at the frame's resolution, and fold that.
    flat = vb.Canvas(w, h, scale=cv.scale, format=cv.format)
    flat.ctx.translate(-x, -y)
    draw_flat(flat)

    def height(i, t):                   # vertical scale at fraction t across panel i: ridge 1, valley less
        rise = t if i % 2 == 0 else 1 - t
        return 1 - depth * sin * (1 - rise)

    for i in range(pleats):
        for j in range(slices):
            t0, t1 = j / slices, (j + 1) / slices
            s0, s1 = height(i, t0), height(i, t1)
            sx0 = x + (i + t0) * sw     # source column
            dx0 = left + (i + t0) * sw * cos
            dx1 = left + (i + t1) * sw * cos
            c.save()
            c.move_to(dx0 - pad, cy - h / 2 * s0)
            c.line_to(dx1 + pad, cy - h / 2 * s1)
            c.line_to(dx1 + pad, cy + h / 2 * s1)
            c.line_to(dx0 - pad, cy + h / 2 * s0)
            c.close_path()
            c.clip()
            s = (s0 + s1) / 2
            c.translate(dx0 - sx0 * cos, cy * (1 - s))
            c.scale(max(cos, 1e-3), s)
            c.translate(x, y)
            c.scale(1 / cv.scale, 1 / cv.scale)
            c.set_source_surface(flat.surface, 0, 0)
            c.paint()
            c.restore()
        if sin > 0:                     # the panel turned from the light, darkened; its neighbour barely
            k = shade * sin * (1.0 if i % 2 else 0.25)
            dx0, dx1 = left + i * sw * cos, left + (i + 1) * sw * cos
            c.save()
            c.move_to(dx0, cy - h / 2 * height(i, 0))
            c.line_to(dx1, cy - h / 2 * height(i, 1))
            c.line_to(dx1, cy + h / 2 * height(i, 1))
            c.line_to(dx0, cy + h / 2 * height(i, 0))
            c.close_path()
            c.set_source_rgba(0, 0, 0, k)
            c.fill()
            c.restore()
    return vb.Box(left, y, w * cos, h)


def draw_accordion_text(cv, text, font, cx, cy, p, color, plate=None, padding=(28, 56), **kw):
    """`text` centred at (cx, cy) on an optional `plate` colour, folded as an
    accordion at progress `p` (0 folded -> 1 flat). `padding` is (v, h) px
    of plate around the text. `kw` goes to `draw_accordion_fold`. Returns
    the Box the folded strip takes up."""
    tw, th = vb.text.block_size([text], font)
    w, h = tw + 2 * padding[1], th + 2 * padding[0]
    x, y = cx - w / 2, cy - h / 2

    def flat(cv):
        if plate:
            cv.rect(x, y, w, h, plate)
        vb.text.draw(cv, [text], font, x + padding[1], y + padding[0], color)

    return draw_accordion_fold(cv, flat, x, y, w, h, p, **kw)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.3))
    box = draw_accordion_text(cv, 'UNFOLD', demo.font(150, 900), demo.W / 2, demo.H / 2, p, demo.INK,
                              plate=demo.LINE, pleats=10)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='accordion-fold-text',
    name='Accordion fold text',
    family='typography',
    group='Depth and 3D',
    aliases=('paper fold text', 'pleat reveal', 'fan fold text'),
    definition='A word printed on a strip creased into vertical pleats opens out like a squeezed '
               'paper fan until it lies flat and reads in full.',
    phrasings=('the title unfolds like a folded paper fan',
               'make the word open out from tight zigzag pleats',
               'text that starts crumpled into vertical folds and stretches flat'),
    related=('accordion-fold', 'paper-fold-reveal', 'origami-fold', 'accordion-height-expand', 'wipe-reveal',
             'curtain-reveal'),
    api=('videobuilder.capabilities.typography.accordion_fold_text.draw_accordion_text',
         'videobuilder.capabilities.typography.accordion_fold_text.draw_accordion_fold'),
    demo=lambda: demo.film(draw),
)

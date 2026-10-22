"""Logo mask wipe reveal: a slanted mask edge sweeps across a logo, uncovering
it as it passes, with a thin colour band running just ahead of the edge that
lights up only where the logo is."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba


def mask_wipe(cv, draw, x, y, w, h, p, slant=0.3, band=28, band_color=demo.ACCENT):
    """Draw `draw(cv)` revealed by a wipe at progress `p` (0 -> 1) over the
    box (x, y, w, h) that holds it: everything left of a leaning edge shows.
    The edge leans forward by `slant` x `h` from bottom to top and enters and
    leaves the box completely, so `p` = 0 shows nothing and 1 shows it all.
    A `band` px strip of `band_color` rides just ahead of the edge, painted
    only on the logo's own pixels (0 for a bare edge). Ease `p` yourself.

    In a film: `mask_wipe(cv, lambda c: my_logo(c), *logo_box, vb.ease_in_out_quart(t / 1.2))`."""
    p = vb.clamp01(p)
    if p <= 0:
        return
    if p >= 1:
        draw(cv)
        return
    s = slant * h
    ex = x - s / 2 - band + (w + s + 2 * band) * p  # edge x at mid-height
    c = cv.ctx

    def wedge(left, right):  # the slanted strip between two edge positions
        c.move_to(left + s / 2, y - 1)
        c.line_to(right + s / 2, y - 1)
        c.line_to(right - s / 2, y + h + 1)
        c.line_to(left - s / 2, y + h + 1)
        c.close_path()

    c.save()
    wedge(x - s - band - 1, ex)
    c.clip()
    draw(cv)
    c.restore()
    if band > 0:
        c.save()
        c.push_group()
        draw(cv)
        shape = c.pop_group()
        wedge(ex, ex + band)
        c.clip()
        c.set_source_rgba(*rgba(band_color))
        c.mask(shape)
        c.restore()


LOGO_W, LOGO_H = 700, 220


def logo(cv, x, y):
    """The demo's stand-in logo: a monogram badge and a wordmark."""
    cv.rect(x, y, LOGO_H, LOGO_H, demo.INK, radius=40)
    demo.word(cv, 'N', x + LOGO_H / 2, y + LOGO_H / 2, size=150, color=demo.BG, weight=900)
    demo.word(cv, 'NORTH', x + LOGO_H + 30 + (LOGO_W - LOGO_H - 30) / 2, y + LOGO_H / 2, size=120,
              weight=900)


def draw(n, cv):
    x, y = (demo.W - LOGO_W) / 2, (demo.H - LOGO_H) / 2
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.2))
    mask_wipe(cv, lambda c: logo(c, x, y), x, y, LOGO_W, LOGO_H, p)
    cv.mark('logo', x, y, LOGO_W, LOGO_H)


CAPABILITY = Capability(
    id='logo-mask-wipe-reveal',
    name='Logo mask wipe reveal',
    family='shapes',
    group='Logo animation',
    aliases=('matte wipe logo', 'wipe logo', 'mask sweep reveal', 'mask-revealed logo'),
    definition='An angled edge travels across the logo, and the mark appears only on the side '
               'the edge has already passed, as if a cover were being slid off it.',
    phrasings=('wipe the logo on from left to right',
               'have a slanted line sweep across and uncover the logo',
               'the logo gets revealed by a moving mask'),
    related=('luma-wipe', 'image-hover-mask-reveal', 'light-trail-logo-reveal', 'brush-stroke-paint-reveal',
             'text-mask-reveal', 'wipe-reveal'),
    api=('videobuilder.capabilities.shapes.logo_mask_wipe_reveal.mask_wipe',),
    demo=lambda: demo.film(draw),
)

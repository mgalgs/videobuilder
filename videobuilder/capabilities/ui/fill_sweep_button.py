"""Fill Sweep Button: on hover a solid colour slides across the button from
one edge, and the label flips to a contrasting colour exactly where the
fill has reached."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

EDGES = ('left', 'right', 'top', 'bottom')


def _filled(x, y, w, h, p, edge):
    """The part of the box (x, y, w, h) covered at progress `p`, sweeping in from `edge`."""
    if edge == 'left':
        return x, y, w * p, h
    if edge == 'right':
        return x + w * (1 - p), y, w * p, h
    if edge == 'top':
        return x, y, w, h * p
    if edge == 'bottom':
        return x, y + h * (1 - p), w, h * p
    raise ValueError(f'edge must be one of {", ".join(EDGES)}, not {edge!r}')


def draw_fill_sweep_button(cv, label, font, x, y, w, h, p, base='#1d1f26', ink=demo.INK, fill=demo.ACCENT,
                           fill_ink=demo.BG, border=demo.LINE, radius=10, edge='left'):
    """Draw a button at (x, y, w, h) with `fill` swept in from `edge` to
    progress `p` (0 = resting, 1 = fully filled). The label is drawn twice,
    `ink` on `base` and `fill_ink` inside the filled part, so its colour
    changes right at the moving edge. Ease `p` yourself (e.g.
    `vb.ease_in_out_quart`); run it back down for hover-out. Returns the
    button's Box."""
    p = vb.clamp01(p)
    tw, th = vb.text.block_size([label], font)
    tx, ty = x + (w - tw) / 2, y + (h - th) / 2
    cv.rect(x, y, w, h, base, radius=radius)
    cv.outline(x, y, w, h, border, width=2, radius=radius)
    vb.text.draw(cv, [label], font, tx, ty, ink)
    if p > 0:
        with cv.clip(x, y, w, h, radius), cv.clip(*_filled(x, y, w, h, p, edge)):
            cv.rect(x, y, w, h, fill)
            vb.text.draw(cv, [label], font, tx, ty, fill_ink)
    return vb.Box(x, y, w, h)


def _pointer(cv, x, y, s=1.0):
    """A plain arrow mouse pointer with its tip at (x, y)."""
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.line_to if i else c.move_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba('#000000'))
    c.set_line_width(2.5 * s)
    c.set_line_join(1)  # round
    c.stroke()


def draw(n, cv):
    w, h = 300, 76
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    box = draw_fill_sweep_button(cv, 'Continue  →', demo.font(30, 800), x, y, w, h,
                                 vb.ease_in_out_quart(demo.phase(n, 1.5, 2.7)))
    cv.mark('button', *box)
    glide = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.4))
    _pointer(cv, 770 + (x + w * 0.84 - 770) * glide, 430 + (y + h * 0.62 - 430) * glide, s=0.9)


CAPABILITY = Capability(
    id='fill-sweep-button',
    name='Fill sweep button',
    family='ui',
    group='Buttons',
    aliases=('wipe fill', 'background wipe', 'sliding fill hover'),
    definition='When the pointer lands on a button, a block of colour slides across it from one side, '
               'and the label switches colour right at the advancing edge.',
    phrasings=('the button fills with colour from left to right when you hover it',
               'a hover state where a colour bar wipes across the button',
               'make the button background slide in on mouse-over and flip the text colour'),
    related=('shape-fill-sweep', 'area-fill-sweep', 'linear-wipe', 'drip-wipe', 'diagonal-wipe', 'wipe-reveal'),
    api=('videobuilder.capabilities.ui.fill_sweep_button.draw_fill_sweep_button',),
    demo=lambda: demo.film(draw),
)

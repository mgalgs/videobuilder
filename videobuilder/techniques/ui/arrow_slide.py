"""Arrow slide: on hover, a button's arrow slides out past its edge and a fresh
copy of it slides in from the other side to take its place."""
import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def draw_arrow(cv, x, y, size, color, width=None, alpha=1.0):
    """A right-pointing line arrow, its tip at (x, y) and `size` px long, with
    round caps and joins."""
    if alpha <= 0:
        return
    c = cv.ctx
    head = size * 0.42
    c.save()
    c.new_path()
    c.move_to(x - size, y)
    c.line_to(x, y)
    c.move_to(x - head, y - head)
    c.line_to(x, y)
    c.line_to(x - head, y + head)
    c.set_line_cap(1)   # cairo.LINE_CAP_ROUND
    c.set_line_join(1)  # cairo.LINE_JOIN_ROUND
    c.set_line_width(width or max(1.5, size * 0.13))
    c.set_source_rgba(*rgba(color, alpha))
    c.stroke()
    c.restore()


def draw_arrow_slide(cv, x, y, size, p, color, travel=None, overlap=0.35, ease=vb.ease_out_quint, **kw):
    """The arrow slide at progress `p` (0 -> 1), the arrow's tip resting at
    (x, y). The resting arrow leaves to the right by `travel` px (default
    `size`) and fades; a second one comes in from `travel` px to the left and
    lands on the rest point. `overlap` is how much of the run the two share.
    Both are clipped to a window around the rest point so neither shows
    outside it. `kw` goes to `draw_arrow`. At 0 and 1 the arrow is at rest."""
    travel = size if travel is None else travel
    p = vb.clamp01(p)
    span = (1 + overlap) / 2
    out, inn = ease(vb.clamp01(p / span)), ease(vb.clamp01((p - (1 - span)) / span))
    pad = size * 0.5
    with cv.clip(x - size - pad, y - size, size + 2 * pad, 2 * size):
        if p < 1:
            draw_arrow(cv, x + travel * out, y, size, color, alpha=1 - out, **kw)
        if p > 0:
            draw_arrow(cv, x - travel * (1 - inn), y, size, color, alpha=inn, **kw)


def draw_arrow_button(cv, cx, cy, label, hover, font, w=None, h=None, color='#1d1f26', ink=demo.INK,
                      edge=demo.LINE, radius=None, p=None):
    """A button centred at (cx, cy): `label` then an arrow, which runs the
    arrow slide at progress `p` (default: `hover`). `hover` (0 -> 1) also
    lifts the fill and edge a little. `w`/`h` default to fit the label.
    Returns the button's Box."""
    lw, lh = vb.text.block_size([label], font)
    size = lh * 0.6
    gap = lh * 0.7
    h = h or lh * 2.3
    w = w or lw + gap + size + h * 1.3
    x, y = cx - w / 2, cy - h / 2
    radius = h * 0.22 if radius is None else radius
    hv = vb.clamp01(hover)
    cv.rect(x, y, w, h, color, radius=radius)
    cv.rect(x, y, w, h, ink, radius=radius, alpha=0.05 * hv)
    cv.outline(x + 0.5, y + 0.5, w - 1, h - 1, edge, width=1.5, radius=radius)
    cv.outline(x + 0.5, y + 0.5, w - 1, h - 1, ink, width=1.5, radius=radius, alpha=0.18 * hv)
    left = cx - (lw + gap + size) / 2
    vb.text.draw(cv, [label], font, left, cy - lh / 2, ink)
    draw_arrow_slide(cv, left + lw + gap + size, cy, size, hover if p is None else p, ink)
    cv.mark('button', x, y, w, h)
    return vb.Box(x, y, w, h)


def _pointer(cv, x, y, s=1.0):
    """A mouse pointer with its tip at (x, y)."""
    pts = [(0, 0), (0, 25), (6, 19.5), (10.5, 29), (14.5, 27.2), (10.2, 18), (18, 18)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*rgba(demo.BG))
    c.set_line_width(1.6 * s)
    c.set_line_join(1)
    c.stroke()


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    move = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.0))
    px = 760 + (cx - 30 - 760) * move
    py = 470 + (cy + 28 - 470) * move
    draw_arrow_button(cv, cx, cy, 'Continue', demo.phase(n, 0.9, 1.15), demo.font(52, 700),
                      p=demo.phase(n, 1.0, 2.0))
    _pointer(cv, px, py, s=1.3)


TECHNIQUE = Technique(
    id='arrow-slide',
    name='Arrow slide',
    family='ui',
    group='Buttons',
    aliases=('arrow nudge', 'directional hover arrow'),
    definition="When a button is hovered, its arrow glides off past its edge while a twin arrow "
               "glides in from behind to settle in the same spot.",
    phrasings=('the arrow on the button slides away and a new one slides in when you hover it',
               'hover the Continue button and its arrow loops through',
               'a next-button arrow that shoots off and comes back from the left'),
    related=('arrow-pointer-draw', 'range-slider-value-bubble', 'tooltip-fade-follow',
             'hover-reveal-actions', 'character-slide-in', 'cursor-follower-dot-and-ring'),
    api=('videobuilder.techniques.ui.arrow_slide.draw_arrow_slide',
         'videobuilder.techniques.ui.arrow_slide.draw_arrow_button',
         'videobuilder.techniques.ui.arrow_slide.draw_arrow'),
    demo=lambda: demo.film(draw),
)

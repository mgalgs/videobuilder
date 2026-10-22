"""Checkbox Check Draw: an empty checkbox fills with colour, gives a small
squeeze, and a tick strokes itself on inside it -- the short leg first, then
the long one. Built on `vb.paths.reveal` and `vb.paths.draw`."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def check_points(x, y, size):
    """The tick inside a `size` box whose top-left is (x, y): three points,
    down the short leg to the elbow, then up the long leg."""
    return [(x + size * 0.24, y + size * 0.52),
            (x + size * 0.42, y + size * 0.70),
            (x + size * 0.77, y + size * 0.32)]


def draw_checkbox(cv, x, y, size, p, color=demo.TEAL, tick=demo.BG, border=demo.MUTED, fill_share=0.35,
                  squeeze=0.12):
    """A checkbox at top-left (x, y), `size` px square, being checked at
    progress `p` (0 -> 1). Over the first `fill_share` of `p` the box floods
    with `color` from its centre and dips by `squeeze` of its size before
    springing back; from there to 1 the `tick` strokes on along
    `check_points`. `p <= 0` is the empty box with its `border`; `p >= 1` is
    the finished check. Returns the Box of the checkbox."""
    p = vb.clamp01(p)
    f = vb.clamp01(p / fill_share)
    t = vb.clamp01((p - fill_share * 0.8) / (1 - fill_share * 0.8))
    s = 1 - squeeze * (4 * f * (1 - f))          # dips mid-fill, back to full size when filled
    cx, cy = x + size / 2, y + size / 2
    w = size * s
    bx, by, r = cx - w / 2, cy - w / 2, size * 0.2
    cv.outline(bx, by, w, w, border, width=max(2, size * 0.05), radius=r, alpha=1 - f)
    if f > 0:
        k = vb.ease_out_quint(f)
        cv.rect(cx - w * k / 2, cy - w * k / 2, w * k, w * k, color, radius=r * k)
    if t > 0:
        pts = [(cx + (px - cx) * s, cy + (py - cy) * s) for px, py in check_points(x, y, size)]
        vb.paths.draw(cv, vb.paths.reveal(pts, vb.ease_in_out_quart(t)), tick, width=size * 0.11)
    return vb.Box(x, y, size, size)


def draw(n, cv):
    size, f = 150, demo.font(64, 700)
    label = 'Task done'
    lw, lh = vb.text.block_size([label], f)
    gap = 48
    x = (demo.W - size - gap - lw) / 2
    y = (demo.H - size) / 2
    p = demo.phase(n, 0.6, 1.9)
    box = draw_checkbox(cv, x, y, size, p)
    cv.mark('checkbox', *box)
    demo.word(cv, label, x + size + gap + lw / 2, demo.H / 2, size=64, weight=700,
              color=demo.INK if p >= 1 else demo.MUTED, alpha=1.0)


CAPABILITY = Capability(
    id='checkbox-check-draw',
    name='Checkbox check draw',
    family='ui',
    group='Toggles & controls',
    aliases=('animated checkbox', 'check tick draw-on', 'checkmark stroke animation'),
    definition='An empty checkbox floods with colour and gives a small squeeze while a tick mark '
               'strokes itself on inside it, short leg first and then the long one.',
    phrasings=('the box gets ticked with the checkmark drawing itself in',
               'animate the checkbox being checked off',
               'a to-do item whose box fills and a tick draws on'),
    related=('circle-check-draw', 'border-draw-button', 'stroke-draw-on', 'stroke-draw-logo-loader',
             'loading-to-success-morph', 'line-draw-logo-reveal'),
    api=('videobuilder.capabilities.ui.checkbox_check_draw.draw_checkbox',
         'videobuilder.capabilities.ui.checkbox_check_draw.check_points',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

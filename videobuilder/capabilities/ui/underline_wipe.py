"""Underline Wipe: a link's underline draws out from one end to full width
when the pointer arrives, then, when it leaves, slides off the far end
rather than shrinking back the way it came."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def underline_span(grow, shrink, side='left'):
    """The underline's ends `(a, b)` as fractions 0..1 of the text width.
    `grow` (0 -> 1, hover in) pushes the leading end across from `side`;
    `shrink` (0 -> 1, hover out) pulls the trailing end after it, so the line
    exits on the opposite side. Both are taken as already eased."""
    grow, shrink = vb.clamp01(grow), vb.clamp01(shrink)
    a, b = shrink * grow, grow
    return (a, b) if side == 'left' else (1 - b, 1 - a)


def draw_underline_wipe(cv, box, grow, shrink=0.0, color=demo.ACCENT, thickness=None, gap=None, side='left',
                        alpha=1.0):
    """Draw the underline under `box` (a `vb.Box`, usually what `vb.text.draw`
    returned) at hover-in progress `grow` and hover-out progress `shrink`
    (see `underline_span`). `thickness` and `gap` default to fractions of the
    box height. Draws nothing while the line has no length."""
    a, b = underline_span(grow, shrink, side)
    if b - a <= 1e-4:
        return
    t = thickness or max(2.0, box.h * 0.07)
    y = box.y + box.h + (box.h * 0.08 if gap is None else gap)
    cv.rect(box.x + box.w * a, y, box.w * (b - a), t, color, radius=t / 2, alpha=alpha)


def _pointer(cv, x, y, s=1.0):
    """A plain arrow cursor with its tip at (x, y)."""
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.move_to if i == 0 else c.line_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(2.5 * s)
    c.stroke()


def draw(n, cv):
    box = demo.word(cv, 'MOTION', demo.W / 2, demo.H / 2, size=110)
    cv.mark('text', *box)
    grow = vb.ease_out_quint(demo.phase(n, 0.75, 1.3))
    shrink = vb.ease_out_quint(demo.phase(n, 2.0, 2.55))
    draw_underline_wipe(cv, box, grow, shrink)
    # the pointer drifts onto the word, rests, then drifts off
    t = n / demo.FPS
    ts = (0.0, 0.75, 2.0, 2.6)
    xs = (box.x + box.w * 1.15, box.x + box.w * 0.7, box.x + box.w * 0.7, box.x + box.w * 1.25)
    ys = (box.y + box.h * 1.5, box.y + box.h * 0.6, box.y + box.h * 0.6, box.y + box.h * 1.7)
    _pointer(cv, vb.interpolate(t, ts, xs, vb.ease_in_out_quart),
             vb.interpolate(t, ts, ys, vb.ease_in_out_quart), s=1.3)


TECHNIQUE = Technique(
    id='underline-wipe',
    name='Underline wipe',
    family='ui',
    group='Cursor & hover',
    aliases=('link underline slide', 'text underline fill', 'hover underline'),
    definition='When the pointer rests on a link a line draws out beneath it from one end to the other, '
               'and when the pointer leaves the line carries on and slides away off the far end.',
    phrasings=('on hover the link gets an underline that sweeps in from the left',
               'an underline that grows under the text when you mouse over it and slides out when you leave',
               'animated link underline that wipes in and wipes out the other side'),
    related=('wipe-reveal', 'tab-underline-slide', 'underline-swash-draw', 'highlighter-swipe',
             'input-underline-grow', 'linear-wipe'),
    api=('videobuilder.techniques.ui.underline_wipe.draw_underline_wipe',
         'videobuilder.techniques.ui.underline_wipe.underline_span'),
    demo=lambda: demo.film(draw),
)

"""Strike-through draw: a pen line is pulled across a word from left to right,
crossing it out, and the struck word dims once the line is through."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def strike_path(box, overshoot=0.08, height=0.52, tilt=-0.06, wobble=2.0, seed=0, step=6):
    """The point list of a strike across `box`, left to right: it starts and
    ends `overshoot` (share of the width) past the box's sides, crosses at
    `height` (share of the height from the top), climbs `tilt` px per px of
    length (negative rises to the right) and wanders about `wobble` px like a
    hand-drawn line, seeded by `seed`."""
    x, y, w, h = box
    ext = w * overshoot
    x0, x1 = x - ext, x + w + ext
    n = max(2, int((x1 - x0) / step))
    mid = y + h * height
    pts = [(x0 + (x1 - x0) * i / n, mid + tilt * ((x1 - x0) * i / n - (x1 - x0) / 2)) for i in range(n + 1)]
    return vb.paths.jitter(pts, seed, amount=wobble, wander=0.15) if wobble else pts


def strike_through(cv, box, p, color=demo.ACCENT, width=None, alpha=1.0, **kw):
    """Draw a strike across `box` (x, y, w, h) at progress `p` (0 -> 1, left
    to right; ease it yourself, e.g. `vb.ease_in_out_quart`): a round-capped
    pen line `width` px thick (default 9% of the box height), shaped by
    `strike_path(box, **kw)`. Draw it after the word so it sits on top.
    Returns the pen tip's (x, y), or None before the line has started."""
    p = vb.clamp01(p)
    if p <= 0:
        return None
    pts = vb.paths.reveal(strike_path(box, **kw), p)
    width = width or max(2.0, box[3] * 0.09)
    if len(pts) >= 2:
        vb.paths.draw(cv, pts, color, width=width, alpha=alpha)
    return pts[-1]


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'MONDAY'
    p = vb.ease_in_out_quart(demo.phase(n, 0.7, 1.6))
    dim = vb.ease_out_quint(demo.phase(n, 1.6, 2.1))
    box = demo.word(cv, text, demo.W / 2, demo.H / 2, font=f, color=demo.INK, alpha=1 - 0.55 * dim)
    cv.mark('word', *box)
    tip = strike_through(cv, (box.x, box.y, box.w, box.h), p, seed=4)
    if tip and p < 1:
        demo.dot(cv, *tip, r=10, color=demo.ACCENT)


TECHNIQUE = Technique(
    id='strike-through-draw',
    name='Strike-through draw',
    family='broadcast',
    group='Annotation',
    aliases=('cross-out', 'strikethrough reveal', 'animated strikethrough'),
    definition='A pen line is drawn across a word or number from one end to the other, '
               'crossing it out to show it no longer stands.',
    phrasings=('draw a line through the old price to cross it out',
               'animate a strikethrough over that word like someone scratched it off',
               'cross out the old date with a hand-drawn line'),
    related=('stroke-draw-on', 'line-draw-logo-reveal', 'line-chart-draw-on', 'wipe-reveal', 'line-weave',
             'highlighter-swipe'),
    api=('videobuilder.techniques.broadcast.strike_through_draw.strike_through',
         'videobuilder.techniques.broadcast.strike_through_draw.strike_path'),
    demo=lambda: demo.film(draw),
)

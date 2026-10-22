"""Range Slider Value Bubble: while a slider's thumb is dragged, a small
callout pops up above it, rides along with the thumb and shows the current
number, then tucks away when the thumb is let go."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def draw_slider(cv, x, y, w, value, bubble=0.0, lo=0, hi=100, color=demo.ACCENT, track=demo.LINE,
                ink=demo.BG, thumb=18, label=None, font=None):
    """A horizontal range slider whose track runs from (x, y) to (x + w, y),
    its thumb at `value` between `lo` and `hi`, the filled part in `color`.

    `bubble` (0 -> 1) is how far the value callout has popped up above the
    thumb: 0 hidden, 1 fully shown; ease it in on grab and out on release
    (`vb.ease_out_back` gives the pop). The callout shows `label`, or the
    value rounded to a whole number. Returns the thumb's centre (tx, y), for
    a cursor to sit on."""
    p = vb.clamp01((value - lo) / (hi - lo))
    tx, bar = x + w * p, max(4, thumb * 0.4)
    cv.rect(x, y - bar / 2, w, bar, track, radius=bar / 2)
    cv.rect(x, y - bar / 2, tx - x, bar, color, radius=bar / 2)
    cv.shadow(tx - thumb, y - thumb, 2 * thumb, 2 * thumb, radius=thumb, dy=3, blur=10, color=(0, 0, 0, 0.4))
    demo.dot(cv, tx, y, thumb, color=demo.INK)
    demo.dot(cv, tx, y, thumb * 0.42, color=color)
    cv.mark('thumb', tx - thumb, y - thumb, 2 * thumb, 2 * thumb)
    if bubble > 0:
        _bubble(cv, tx, y - thumb - 8, label if label is not None else str(round(value)),
                font or demo.mono(round(thumb * 1.5), 800), bubble, color, ink)
    return tx, y


def _bubble(cv, cx, tip, text, font, s, color, ink):
    """The callout: a rounded tag with a pointer whose tip is at (cx, tip),
    grown about that tip by `s` and faded in over the first part of it."""
    tw, th = vb.text.block_size([text], font)
    bh, nub = th + 14, 8
    bw = max(tw + 24, bh)
    c = cv.ctx
    with cv.layer(opacity=min(1.0, max(0.0, s) * 2.5), dx=cx, dy=tip + 10 * (1 - s), scale=max(0.01, s)):
        top = -nub - bh
        cv.shadow(-bw / 2, top, bw, bh, radius=12, dy=6, blur=16, color=(0, 0, 0, 0.35))
        cv.rect(-bw / 2, top, bw, bh, color, radius=12)
        c.move_to(-nub, -nub - 1)
        c.line_to(nub, -nub - 1)
        c.line_to(0, 0)
        c.close_path()
        c.set_source_rgba(*vb.rgba(color))
        c.fill()
        vb.text.draw(cv, [text], font, -tw / 2, top + (bh - th) / 2, ink)
        cv.mark('bubble', -bw / 2, top, bw, bh)


def _cursor(cv, x, y, size=34, pressed=0.0):
    """A plain arrow pointer with its tip at (x, y), dipping slightly when pressed."""
    pts = [(0, 0), (0, 1.0), (0.27, 0.76), (0.45, 1.12), (0.6, 1.05), (0.42, 0.7), (0.74, 0.7)]
    k = size * (1 - 0.12 * pressed)
    c = cv.ctx
    for fill, grow in ((demo.BG, 3.5), (demo.INK, 0)):
        c.new_path()
        for i, (px, py) in enumerate(pts):
            (c.move_to if i == 0 else c.line_to)(x + px * k, y + py * k)
        c.close_path()
        c.set_source_rgba(*vb.rgba(fill))
        if grow:
            c.set_line_width(grow)
            c.set_line_join(1)  # round
            c.stroke_preserve()
        c.fill()


# The drag in the demo: (seconds, value) keys; the thumb is held from GRAB to LET_GO.
KEYS = ((0.0, 30), (0.55, 30), (1.35, 78), (1.6, 78), (2.35, 27), (3.0, 27))
GRAB, LET_GO = 0.45, 2.45


def draw(n, cv):
    t = n / demo.FPS
    xs, ys = zip(*KEYS)
    value = vb.interpolate(t, xs, ys, ease=vb.ease_in_out_quart)
    shown = (vb.ease_out_back(demo.phase(n, GRAB, GRAB + 0.3))
             * (1 - vb.ease_in_expo(demo.phase(n, LET_GO, LET_GO + 0.25))))
    held = demo.phase(n, GRAB, GRAB + 0.1) * (1 - demo.phase(n, LET_GO, LET_GO + 0.1))
    w = 620
    tx, ty = draw_slider(cv, (demo.W - w) / 2, demo.H / 2 + 30, w, value, bubble=shown, thumb=14)
    approach = 1 - vb.ease_out_quint(demo.phase(n, 0.0, GRAB))  # the pointer glides onto the thumb first
    _cursor(cv, tx + 4 + 40 * approach, ty + 3 + 60 * approach, size=24, pressed=held)


TECHNIQUE = Technique(
    id='range-slider-value-bubble',
    name='Range slider value bubble',
    family='ui',
    group='Toggles & controls',
    aliases=('slider tooltip', 'thumb label follow', 'slider value label'),
    definition='A little tag pops up over a slider handle as it is dragged, slides along with it '
               'showing the live number, and disappears when the handle is released.',
    phrasings=('show the number above the slider knob while I drag it',
               'a slider with a little popup that follows the handle and shows the value',
               'drag the volume slider and have the value appear in a bubble over the thumb'),
    related=('tooltip-fade-follow', 'arrow-slide', 'before-after-slider', 'dock-magnification',
             'cursor-state-change', 'carousel-slide'),
    api=('videobuilder.techniques.ui.range_slider_value_bubble.draw_slider',),
    demo=lambda: demo.film(draw),
)

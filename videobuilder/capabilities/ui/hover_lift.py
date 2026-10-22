"""Hover Lift: a button floats up a few pixels while the pointer is over it,
its shadow growing longer and softer underneath, and sinks back when the
pointer leaves."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def hover(t, enter, leave, up=0.18, down=0.28):
    """How lifted (0 -> 1) a hovered element is at time `t`, the pointer
    arriving at `enter` and leaving at `leave` (all seconds): it eases up over
    `up` seconds and settles back over `down`, starting from wherever it had
    got to if the pointer leaves before the lift finished."""
    rising = vb.interpolate(t, [enter, enter + up], [0, 1], ease=vb.ease_out_quint)
    if t < leave:
        return rising
    top = vb.interpolate(leave, [enter, enter + up], [0, 1], ease=vb.ease_out_quint)
    return top * (1 - vb.interpolate(t, [leave, leave + down], [0, 1], ease=vb.ease_in_out_quart))


def draw_lift(cv, x, y, w, h, lift, color, radius=14, rise=10, label=None, font=None, ink=demo.INK):
    """A button resting at the box (x, y, w, h), raised `rise` px times `lift`
    (0 at rest, 1 fully hovered). The shadow stays on the ground and deepens as
    the button rises: further offset, wider blur, darker. `label` is centred
    in `font` and `ink`. Returns the button's Box as drawn."""
    lift = vb.clamp01(lift)
    by = y - rise * lift
    cv.shadow(x, y, w, h, radius=radius, dy=2 + 12 * lift, blur=6 + 24 * lift, spread=-2 * lift,
              color=(0, 0, 0, 0.3 + 0.3 * lift))
    cv.rect(x, by, w, h, color, radius=radius)
    cv.rect(x, by, w, h, '#ffffff', radius=radius, alpha=0.08 * lift)  # a touch brighter as it comes up
    if label:
        f = font or demo.font(round(h * 0.36), 700)
        demo.word(cv, label, x + w / 2, by + h / 2, font=f, color=ink)
    return vb.Box(x, by, w, h)


def pointer(cv, x, y, alpha=1.0, scale=1.2):
    """An arrow pointer with its tip at (x, y)."""
    pts = [(x + px * scale, y + py * scale) for px, py in ARROW]
    with cv.layer(opacity=alpha):
        cv.shape_shadow(pts, dx=2, dy=3, blur=5, color=(0, 0, 0, 0.45))
        cv.ctx.new_path()
        cv.ctx.move_to(*pts[0])
        for pt in pts[1:]:
            cv.ctx.line_to(*pt)
        cv.ctx.close_path()
        cv.ctx.set_source_rgba(*vb.rgba(demo.INK))
        cv.ctx.fill_preserve()
        cv.ctx.set_source_rgba(*vb.rgba(demo.BG))
        cv.ctx.set_line_width(2)
        cv.ctx.stroke()


def draw(n, cv):
    t = n / demo.FPS
    w, h = 300, 84
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    box = draw_lift(cv, x, y, w, h, hover(t, 0.9, 2.05), demo.ACCENT, label='Get started')
    cv.mark('button', *box)
    # The pointer glides in from the lower right, rests on the button, then drifts off.
    start, on = (demo.W - 170, demo.H - 70), (x + w * 0.62, y + h * 0.55)
    come = vb.interpolate(t, [0.3, 0.9], [0, 1], ease=vb.ease_in_out_quart)
    go = vb.interpolate(t, [2.0, 2.6], [0, 1], ease=vb.ease_in_out_quart)
    px = start[0] + (on[0] - start[0]) * come + (start[0] - on[0]) * 0.8 * go
    py = start[1] + (on[1] - start[1]) * come + (start[1] - on[1]) * 0.8 * go
    pointer(cv, px, py)


TECHNIQUE = Technique(
    id='hover-lift',
    name='Hover lift',
    family='ui',
    group='Buttons',
    aliases=('hover elevate', 'raise on hover', 'hover raise'),
    definition='When the pointer moves onto a button it floats up slightly with a bigger, softer shadow '
               'beneath it, and drops back down once the pointer moves away.',
    phrasings=('the button pops up a little when the mouse goes over it',
               'make the button rise off the page on hover',
               'mouse over the button and it lifts with a deeper shadow'),
    related=('drag-lift-with-shadow', 'drop-shadow-lift', 'spotlight-hover', 'hover-letter-displacement',
             'hover-reveal-actions', 'icon-hover-bounce'),
    api=('videobuilder.techniques.ui.hover_lift.draw_lift',
         'videobuilder.techniques.ui.hover_lift.hover',
         'videobuilder.techniques.ui.hover_lift.pointer'),
    demo=lambda: demo.film(draw),
)

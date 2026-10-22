"""Magnetic button: as the pointer comes near, the button leans toward it and
its label leans a little further, then both settle back once it moves away."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def magnetic_pull(cx, cy, px, py, reach=260, inner=90, strength=0.4):
    """How far a button centred at (cx, cy) shifts toward a pointer at
    (px, py), as `(dx, dy)`: `strength` times the pointer's offset while it
    is within `inner` of the centre, fading smoothly to nothing at `reach`.
    A pure function of where the pointer is, so any frame evaluates alone."""
    vx, vy = px - cx, py - cy
    d = math.hypot(vx, vy)
    if d >= reach:
        return 0.0, 0.0
    t = vb.clamp01((reach - d) / (reach - inner))
    w = strength * t * t * (3 - 2 * t)
    return vx * w, vy * w


def draw_magnetic_button(cv, text, cx, cy, px, py, font, color, ink, pad=(56, 30), label_gain=1.6, **kw):
    """Draw a pill button labelled `text` at rest centre (cx, cy), pulled
    toward a pointer at (px, py) by `magnetic_pull` (`kw` passes through);
    the label is pulled `label_gain` times as far, so it leads the pill.
    Returns the Box the pill was drawn in."""
    dx, dy = magnetic_pull(cx, cy, px, py, **kw)
    tw, th = vb.text.block_size([text], font)
    w, h = tw + 2 * pad[0], th + 2 * pad[1]
    x, y = cx + dx - w / 2, cy + dy - h / 2
    cv.shadow(x, y, w, h, radius=h / 2, dy=10, blur=26, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, color, radius=h / 2)
    vb.text.draw(cv, [text], font, cx + dx * label_gain - tw / 2, cy + dy * label_gain - th / 2, ink)
    return vb.Box(x, y, w, h)


def _pointer(cv, x, y, s=1.6):
    pts = [(x + px * s, y + py * s) for px, py in ARROW]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    ctx = cv.ctx
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(demo.INK))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(demo.BG))
    ctx.set_line_width(2)
    ctx.stroke()


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    t = n / demo.FPS
    # The pointer drifts in from the lower right, hovers over the button, then wanders off again.
    keys = (0.0, 0.3, 1.0, 1.5, 1.9, 2.6, 3.0)
    xs = (cx + 330, cx + 330, cx - 110, cx - 60, cx + 90, cx + 380, cx + 380)
    ys = (cy + 230, cy + 230, cy + 25, cy - 35, cy + 15, cy + 200, cy + 200)
    px = vb.interpolate(t, keys, xs, ease=vb.ease_in_out_quart)
    py = vb.interpolate(t, keys, ys, ease=vb.ease_in_out_quart)
    f = demo.font(44, 800)
    tw, th = vb.text.block_size(['Explore'], f)
    w, h = tw + 112, th + 60
    cv.outline(cx - w / 2, cy - h / 2, w, h, demo.MUTED, width=2, radius=h / 2, alpha=0.35)  # where it rests
    box = draw_magnetic_button(cv, 'Explore', cx, cy, px, py, f, demo.ACCENT, demo.BG)
    cv.mark('button', *box)
    _pointer(cv, px, py)


CAPABILITY = Capability(
    id='magnetic-button',
    name='Magnetic button',
    family='ui',
    group='Buttons',
    aliases=('cursor attraction', 'pointer pull', 'magnetic hover'),
    definition='A button that leans toward a nearby pointer, its label shifting a bit more than the pill, '
               'and eases back to its spot when the pointer goes away.',
    phrasings=('the button gets pulled toward the mouse when you hover near it',
               'a sticky hover where the button follows the cursor a little',
               'the call-to-action is drawn to the pointer like a magnet and snaps back after'),
    related=('spring-drag-letters', 'magnetic-snap', 'cursor-path-animation', 'cursor-state-change',
             'cursor-particle-trail', 'cursor-follower-dot-and-ring'),
    api=('videobuilder.capabilities.ui.magnetic_button.draw_magnetic_button',
         'videobuilder.capabilities.ui.magnetic_button.magnetic_pull'),
    demo=lambda: demo.film(draw),
)

"""Drop Target Highlight: a dashed, quiet drop zone wakes up when a dragged
item passes over it -- its edge turns solid in the accent colour, its inside
tints, and a soft glow breathes around it until the item is let go."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def drop_target(cv, x, y, w, h, hover, t=0.0, color=demo.ACCENT, idle=demo.MUTED, radius=18,
                dash=14, pulse_hz=1.6, glow=14, pulse=1.0):
    """Draw a drop zone over the box (x, y, w, h). `hover` (0 -> 1) is how
    awake it is: 0 is the idle state, a thin dashed `idle` outline; 1 is a
    solid `color` edge, a tinted fill and a glow `glow` px deep that pulses
    `pulse_hz` times a second with the time `t` (seconds). Ease `hover` in
    when the item enters and out if it leaves; on a drop, ease `pulse`
    (1 -> 0) instead to settle the glow while the edge stays lit."""
    hover = vb.clamp01(hover)
    c = cv.ctx
    if hover < 1:  # the idle dashed edge fades out as the solid one fades in
        c.save()
        c.set_dash([dash, dash * 0.7])
        cv.outline(x, y, w, h, idle, width=2, radius=radius, alpha=0.7 * (1 - hover))
        c.restore()
    if hover <= 0:
        return
    beat = 0.5 + 0.5 * math.sin(2 * math.pi * pulse_hz * t)
    cv.rect(x, y, w, h, color, radius=radius, alpha=hover * (0.04 + pulse * (0.03 + 0.05 * beat)))
    reach = glow * (0.6 + 0.4 * beat)
    for i in range(6, 0, -1):  # the glow: wide faint strokes under a narrow bright one
        cv.outline(x, y, w, h, color, width=reach * i / 3, radius=radius, alpha=hover * pulse * 0.07 * (1 - i / 7))
    cv.outline(x, y, w, h, color, width=2.5, radius=radius, alpha=hover)


def cursor(cv, x, y, color=demo.INK, size=26):
    """A plain arrow pointer with its tip at (x, y)."""
    pts = [(0, 0), (0, 1), (0.27, 0.76), (0.45, 1.12), (0.58, 1.05), (0.4, 0.7), (0.72, 0.7)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.move_to if i == 0 else c.line_to)(x + px * size, y + py * size)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.canvas.rgba(demo.BG))
    c.set_line_width(2)
    c.stroke()


ZONE = (530, 250, 330, 200)       # the drop zone (x, y, w, h)
START = (250, 170)                 # the card's centre before the drag
CW, CH = 240, 150


def draw(n, cv):
    t = n / demo.FPS
    zx, zy, zw, zh = ZONE
    end = (zx + zw / 2, zy + zh / 2)
    lift = demo.phase(n, 0.25, 0.45)                     # picked up
    move = vb.ease_in_out_quart(demo.phase(n, 0.45, 1.6))
    drop = demo.phase(n, 2.15, 2.35)                     # let go
    cx = START[0] + (end[0] - START[0]) * move
    cy = START[1] + (end[1] - START[1]) * move - 40 * math.sin(math.pi * move)
    # the zone wakes as the card overlaps it, and settles to a steady edge once the card lands
    ox = max(0, min(cx + CW / 2, zx + zw) - max(cx - CW / 2, zx))
    oy = max(0, min(cy + CH / 2, zy + zh) - max(cy - CH / 2, zy))
    awake = vb.ease_out_quint(vb.clamp01(4 * ox * oy / (CW * CH)))
    drop_target(cv, zx, zy, zw, zh, awake, t, pulse=1 - vb.ease_out_quint(drop))
    scale = 1 + 0.05 * lift * (1 - drop)
    demo.card(cv, cx, cy, w=CW, h=CH, color=demo.LINE, scale=scale)
    cursor(cv, cx + 60, cy + 20 - 4 * lift * (1 - drop))
    cv.mark('zone', *ZONE)


CAPABILITY = Capability(
    id='drop-target-highlight',
    name='Drop target highlight',
    family='ui',
    group='Gestures & drag',
    aliases=('drop zone glow', 'drag target', 'drop zone highlight'),
    definition='An empty landing area lights up, its outline turning bright and glowing softly, '
               'the moment something being dragged moves over it, showing it will accept the drop.',
    phrasings=('the box lights up when you drag the card over it',
               'make the drop area glow while the item hovers on top',
               'highlight where you can let go of the thing you are dragging'),
    related=('border-glow-follow', 'spotlight-hover', 'glow-button', 'coachmark-spotlight-cutout',
             'map-pin-drop', 'outline-pulse-glow'),
    api=('videobuilder.capabilities.ui.drop_target_highlight.drop_target',
         'videobuilder.capabilities.ui.drop_target_highlight.cursor'),
    demo=lambda: demo.film(draw),
)

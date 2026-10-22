"""Liquid Button: a pill button whose outline behaves like thick fluid -- the
edge nearest the pointer swells out and reaches after it, and when the
pointer lets go the shape springs back, wobbling before it settles."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pill_outline(cx, cy, w, h, n=96):
    """`n` points evenly spaced around a pill (a box with fully round ends)
    centred at (cx, cy), clockwise from the top-left of its straight edge, as
    `(x, y, nx, ny)`: each point and its outward unit normal."""
    r = h / 2
    flat = max(0.0, w - h)
    perimeter = 2 * flat + 2 * math.pi * r
    out = []
    for i in range(n):
        s = perimeter * i / n
        if s < flat:                                    # top edge, left to right
            out.append((cx - flat / 2 + s, cy - r, 0.0, -1.0))
            continue
        s -= flat
        if s < math.pi * r:                             # right cap, top to bottom
            a = -math.pi / 2 + s / r
            out.append((cx + flat / 2 + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))
            continue
        s -= math.pi * r
        if s < flat:                                    # bottom edge, right to left
            out.append((cx + flat / 2 - s, cy + r, 0.0, 1.0))
            continue
        a = math.pi / 2 + (s - flat) / r                # left cap, bottom to top
        out.append((cx - flat / 2 + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))
    return out


def liquid_outline(cx, cy, w, h, toward, pull, spread=60.0, ripple=0.0, phase=0.0, lobes=5, n=96):
    """The deformed outline of a liquid button as a closed list of (x, y).

    `toward` is the pointer (x, y). Edge points near it bulge out along
    their normal and lean toward it by up to `pull` px, falling off over
    `spread` px of distance from the pointer. A negative `pull` dents the
    edge in (the rebound past rest). `ripple` px of `lobes`-lobed wave,
    rotated by `phase` radians, wobbles the whole edge; decay it to zero for
    the settle."""
    px, py = toward
    pts = []
    for i, (x, y, nx, ny) in enumerate(pill_outline(cx, cy, w, h, n)):
        dx, dy = px - x, py - y
        d = math.hypot(dx, dy)
        weight = math.exp(-(d / spread) ** 2)
        push = pull * weight
        lean = 0.3 * push / (d + spread)
        wave = ripple * math.sin(lobes * 2 * math.pi * i / n + phase)
        pts.append((x + nx * (push + wave) + dx * lean, y + ny * (push + wave) + dy * lean))
    return pts


def smooth_path(ctx, pts):
    """Trace the closed point list `pts` on cairo context `ctx` as one smooth
    curve (Catmull-Rom through every point), ready to fill or stroke."""
    n = len(pts)
    ctx.new_path()
    ctx.move_to(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        ctx.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    ctx.close_path()


def draw_liquid_button(cv, cx, cy, w, h, color, toward, pull, label=None, font=None, ink=demo.BG,
                       press=0.0, alpha=1.0, **kw):
    """Draw a liquid pill button centred at (cx, cy), `w` x `h` at rest, its
    edge drawn out toward the pointer `toward` by `pull` px (see
    `liquid_outline`; `kw` goes there: `ripple`, `phase`, `spread`, ...).
    `press` (0 -> 1) squashes the body a little, as when it is clicked.
    `label` is centred in `font` and `ink`. Returns the resting Box."""
    sw, sh = w * (1 + 0.04 * press), h * (1 - 0.1 * press)
    pts = liquid_outline(cx, cy, sw, sh, toward, pull, **kw)
    with cv.layer(opacity=alpha):
        cv.shape_shadow(pts, dy=10, blur=26, color=(0, 0, 0, 0.4))
        smooth_path(cv.ctx, pts)
        cv.ctx.set_source_rgba(*vb.canvas.rgba(color))
        cv.ctx.fill()
        if label:
            demo.word(cv, label, cx, cy, size=round(h * 0.36), color=ink, weight=800, font=font)
    box = vb.Box(cx - w / 2, cy - h / 2, w, h)
    cv.mark('button', *box)
    return box


def _pointer(cv, x, y, s=1.0):
    """A mouse arrow with its tip at (x, y)."""
    arrow = [(0, 0), (0, 25), (6, 19), (10.5, 29), (14.5, 27), (10, 17.5), (18, 17.5)]
    c = cv.ctx
    c.new_path()
    for i, (ax, ay) in enumerate(arrow):
        (c.move_to if i == 0 else c.line_to)(x + ax * s, y + ay * s)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.canvas.rgba(demo.BG))
    c.set_line_width(2)
    c.stroke()


BTN_W, BTN_H = 300, 92
HOVER = (demo.W / 2 + 150, demo.H / 2 - 58)            # just off the top-right of the button
START, END = (demo.W / 2 + 260, demo.H / 2 + 170), (demo.W / 2 + 320, demo.H / 2 + 190)


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    come = vb.ease_in_out_quart(demo.phase(n, 0.2, 0.9))
    go = vb.ease_in_out_quart(demo.phase(n, 1.75, 2.25))
    px = START[0] + (HOVER[0] - START[0]) * come + (END[0] - HOVER[0]) * go
    py = START[1] + (HOVER[1] - START[1]) * come + (END[1] - HOVER[1]) * go
    grab = vb.ease_out_quint(demo.phase(n, 0.6, 1.2))  # the edge swells after the arriving pointer
    snap = vb.spring(t - 1.8, **vb.damped(0.22, hz=2.6)) if t > 1.8 else 0.0  # then lets go and springs back
    pull = 34 * grab * (1 - snap)
    settle = math.exp(-2.2 * max(0.0, t - 1.8)) if t > 1.8 else 0.0
    ripple = 4 * settle * min(1.0, (t - 1.8) * 6) if t > 1.8 else 0.0
    press = math.sin(math.pi * demo.phase(n, 1.2, 1.55))
    draw_liquid_button(cv, cx, cy, BTN_W, BTN_H, '#8a8cff', (px, py), pull, label='Press', press=press,
                       ripple=ripple, phase=t * 9, spread=80)
    _pointer(cv, px - 4 * press, py - 4 * press)


CAPABILITY = Capability(
    id='liquid-button',
    name='Liquid button',
    family='ui',
    group='Buttons',
    aliases=('gooey button', 'viscous press', 'blob button'),
    definition='A button whose edge swells and stretches toward the pointer as if made of thick liquid, '
               'then springs back and wobbles into its normal shape when released.',
    phrasings=('make the button go gooey and reach for the cursor when you hover it',
               'a jelly-like button that bulges under the mouse and snaps back',
               'the button edge melts out toward the pointer, then wobbles back into place'),
    related=('liquid-melt', 'speed-dial-fan', 'bubbles', 'twist-deformer', 'liquid-fill-level', 'circle-pop'),
    api=('videobuilder.capabilities.ui.liquid_button.draw_liquid_button',
         'videobuilder.capabilities.ui.liquid_button.liquid_outline',
         'videobuilder.capabilities.ui.liquid_button.smooth_path'),
    demo=lambda: demo.film(draw),
)

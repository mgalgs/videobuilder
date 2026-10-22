"""Focus Ring Draw: when a control takes keyboard focus, an outline traces
itself around it while easing outward from the control's edge to a small gap,
settling with a slight overshoot."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ring_points(x, y, w, h, radius, start=0.0, per_corner=12):
    """The closed outline of the rounded box (x, y, w, h) as a point list,
    clockwise, beginning `start` (0..1) of the way round from the top-left
    end of the top edge."""
    r = max(0.0, min(radius, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for k in range(per_corner + 1):
            a = math.radians(a0 + 90 * k / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    k = round((start % 1.0) * len(pts))
    return pts[k:] + pts[:k]


def draw_focus_ring(cv, x, y, w, h, p, color=demo.TEAL, width=4, radius=12, gap=7, start=0.62,
                    glow=0.25, alpha=1.0):
    """Draw a focus ring arriving on the control (x, y, w, h) at progress `p`
    (0 -> 1). The stroke traces round from `start` (a fraction of the way
    round, clockwise from the top-left) while its offset from the control's
    edge grows from 0 to `gap` with a small overshoot; `radius` is the
    control's corner radius, the ring's follows it out. `glow` is the opacity
    of a soft wider halo under the stroke (0 for none). At `p >= 1` it is the
    plain resting ring. Returns the ring's Box."""
    p = vb.clamp01(p)
    if p <= 0:
        return None
    off = gap * vb.ease_out_back(p)
    rx, ry, rw, rh = x - off, y - off, w + 2 * off, h + 2 * off
    pts = vb.paths.reveal(ring_points(rx, ry, rw, rh, radius + off, start), 1 - (1 - p) ** 2, closed=True)
    a = alpha * vb.clamp01(p * 4)
    if glow > 0:
        vb.paths.draw(cv, pts, color, width=width * 3.5, alpha=a * glow, closed=p >= 1)
    vb.paths.draw(cv, pts, color, width=width, alpha=a, closed=p >= 1)
    return vb.Box(rx - width / 2, ry - width / 2, rw + width, rh + width)


# ---- demo: a small form, Tab moving focus from a field to a button ----

CARD = (demo.W / 2 - 330, demo.H / 2 - 230, 660, 360)
FIELD = (CARD[0] + 60, CARD[1] + 130, 540, 72)
BUTTON = (CARD[0] + 60, CARD[1] + 250, 200, 64)
TABS = (0.45, 1.65)  # when Tab is pressed


def _key(cv, n):
    cx, cy, w, h = demo.W / 2, CARD[1] + CARD[3] + 110, 96, 64
    press = max(math.exp(-((n / demo.FPS - t) / 0.08) ** 2) for t in TABS)
    dy = 4 * press
    cv.rect(cx - w / 2, cy - h / 2 + 6, w, h, '#0b0d10', radius=12)
    cv.rect(cx - w / 2, cy - h / 2 + dy, w, h, '#2a2f37', radius=12)
    cv.outline(cx - w / 2, cy - h / 2 + dy, w, h, demo.MUTED, width=2, radius=12, alpha=0.6 + 0.4 * press)
    demo.word(cv, 'Tab ⇥', cx, cy + dy, size=26, weight=700, color=demo.INK)


def draw(n, cv):
    x, y, w, h = CARD
    cv.shadow(x, y, w, h, radius=22, dy=12, blur=36, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, '#1d2128', radius=22)
    cv.rect(x + 60, y + 52, 220, 16, demo.INK, radius=8, alpha=0.85)
    cv.rect(x + 60, y + 82, 360, 12, demo.MUTED, radius=6, alpha=0.6)
    fx, fy, fw, fh = FIELD
    cv.rect(fx, fy, fw, fh, '#12151a', radius=12)
    cv.outline(fx, fy, fw, fh, demo.LINE, width=2, radius=12)
    cv.rect(fx + 24, fy + fh / 2 - 7, 190, 14, demo.MUTED, radius=7, alpha=0.5)
    bx, by, bw, bh = BUTTON
    cv.rect(bx, by, bw, bh, demo.ACCENT, radius=12)
    cv.rect(bx + 50, by + bh / 2 - 7, bw - 100, 14, demo.INK, radius=7, alpha=0.95)
    _key(cv, n)

    t1, t2 = TABS
    leave = 1 - demo.phase(n, t2, t2 + 0.15)
    if leave > 0:
        box = draw_focus_ring(cv, *FIELD, demo.phase(n, t1 + 0.05, t1 + 0.85), alpha=leave)
        if box:
            cv.mark('ring', *box)
    box = draw_focus_ring(cv, *BUTTON, demo.phase(n, t2 + 0.05, t2 + 0.85))
    if box:
        cv.mark('ring', *box)


CAPABILITY = Capability(
    id='focus-ring-draw',
    name='Focus ring draw',
    family='ui',
    group='Forms',
    aliases=('keyboard focus outline', 'focus indicator animation', 'animated focus ring'),
    definition='When a control gains keyboard focus, an outline sweeps around it and eases out '
               'to sit a little way off its edge.',
    phrasings=('the outline draws itself around the button when you tab to it',
               'animate the focus highlight moving from field to field as someone presses Tab',
               'a glowing border that traces round the selected input and pops out slightly'),
    related=('highlight-circle-draw', 'character-blur-in', 'focus-blur-out', 'callout-highlight',
             'cursor-follower-dot-and-ring', 'rack-focus'),
    api=('videobuilder.capabilities.ui.focus_ring_draw.draw_focus_ring',
         'videobuilder.capabilities.ui.focus_ring_draw.ring_points'),
    demo=lambda: demo.film(draw),
)

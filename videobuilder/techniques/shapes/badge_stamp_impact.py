"""Badge Stamp Impact: a badge falls onto the frame from above and slightly
too big, slams down on a given frame, squashes, rattles, springs back to
size and settles, a thin ring rippling out from where it hit."""
import math

import videobuilder as vb
from videobuilder import impact

from .. import _demo as demo
from ..schema import Technique


def stamp_pose(n, at, fall=8, height=420, lift=0.4, squash=0.2, shake=12, settle=14, fps=30, seed=0):
    """The badge's pose at frame `n` for a stamp landing on frame `at`, as
    `(dx, dy, scale, ring)`: offset in px from its resting place, scale about
    its centre, and the impact ring's progress 0 -> 1 (None outside it).

    It falls for `fall` frames from `height` px above, `lift` bigger as if
    nearer the camera, speeding up as it comes; lands `squash` small; then
    springs back past full size and settles while shaking by up to `shake` px
    for `settle` frames (`impact.shake`)."""
    k = n - at
    if k < 0:
        p = vb.clamp01((n - (at - fall)) / fall) if fall else 1.0
        g = p * p  # accelerating, like something dropped
        return 0.0, -height * (1 - g), 1 + lift * (1 - g), None
    back = vb.spring_at(k, fps, **vb.damped(0.32, hz=3.5))
    dx, dy = impact.shake(n, at, settle, shake, seed)
    ring = k / (settle + 8)
    return dx, dy, (1 - squash) + squash * back, ring if ring < 1 else None


def draw_badge_stamp(cv, badge, cx, cy, n, at, size=200, ring_color=None, **kw):
    """Draw frame `n` of a stamp landing on frame `at`: `badge(cv)` draws the
    badge centred on (0, 0) about `size` px across; it is placed at (cx, cy)
    in its pose from `stamp_pose` (`kw` goes there). The ring, in
    `ring_color` (default: off), spreads from `size` to twice it and fades.
    Returns the badge's Box at rest."""
    dx, dy, s, ring = stamp_pose(n, at, **kw)
    if ring is not None and ring_color:
        cv.arc(cx, cy, size / 2 * (1.05 + 0.95 * vb.ease_out_expo(ring)), 0, 2 * math.pi, ring_color,
               width=6 * (1 - ring) + 1, alpha=0.8 * (1 - ring))
    with cv.layer(dx=cx + dx, dy=cy + dy, scale=s):
        badge(cv)
    return vb.Box(cx - size / 2, cy - size / 2, size, size)


GOLD = '#f3b81c'


def _badge(cv, r=100, bumps=16):
    """A scalloped seal with an inner ring and a tick, centred on (0, 0)."""
    c = cv.ctx
    c.new_path()
    steps = bumps * 12
    for i in range(steps + 1):
        a = 2 * math.pi * i / steps
        rr = r * (0.93 + 0.07 * math.cos(bumps * a))
        c.line_to(rr * math.cos(a), rr * math.sin(a))
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(GOLD))
    c.fill()
    cv.arc(0, 0, r * 0.74, 0, 2 * math.pi, demo.BG, width=4)
    cv.arc(0, 0, r * 0.67, 0, 2 * math.pi, demo.BG, width=2)
    c.new_path()
    c.move_to(-r * 0.3, 0)
    c.line_to(-r * 0.08, r * 0.22)
    c.line_to(r * 0.32, -r * 0.2)
    c.set_line_width(r * 0.11)
    c.set_line_cap(1)   # round
    c.set_line_join(1)  # round
    c.set_source_rgba(*vb.canvas.rgba(demo.BG))
    c.stroke()


def draw(n, cv):
    box = draw_badge_stamp(cv, _badge, demo.W / 2, demo.H / 2, n, at=30, size=200, ring_color=GOLD, fall=10,
                           height=demo.H / 2 + 200)
    cv.mark('badge', *box)


TECHNIQUE = Technique(
    id='badge-stamp-impact',
    name='Badge stamp impact',
    family='shapes',
    group='Bounce & pop',
    aliases=('stamp slam', 'rubber stamp', 'seal impact', 'stamp down'),
    definition='A badge drops in from above, slams onto its spot with a quick squash and a rattle, '
               'then springs back to size and sits still.',
    phrasings=('slam an approved seal down onto the screen',
               'the badge stamps on with a thud and a little shake',
               'drop a stamp onto the frame like it was hit with a rubber stamp'),
    related=('stamp-impression', 'badge-count-bump', 'map-pin-drop', 'impact-hit', 'impact', 'impact-shake'),
    api=('videobuilder.techniques.shapes.badge_stamp_impact.draw_badge_stamp',
         'videobuilder.techniques.shapes.badge_stamp_impact.stamp_pose',
         'videobuilder.impact.shake'),
    demo=lambda: demo.film(draw),
)

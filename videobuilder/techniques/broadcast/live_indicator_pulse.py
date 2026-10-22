"""Live Indicator Pulse: a small red dot beside a LIVE label throbs on a
steady beat, a soft ring spreading off it each time, so the viewer knows the
feed is running right now."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def live_pulse(t, period=1.2, start=0.0):
    """The beat of a live dot at time `t` (seconds) as `(glow, ring)`.
    `glow` runs 0 -> 1 -> 0 once per `period`, peaking a quarter of the way
    in so each beat lands quickly and fades slowly; `ring` is 0 -> 1 across
    the period, the progress of the ring spreading off the dot. Before
    `start` it rests at `(0, 0)`. A whole number of periods across a loop
    keeps the seam clean."""
    if t < start:
        return 0.0, 0.0
    ring = ((t - start) / period) % 1.0
    rise = 0.25
    glow = ring / rise if ring < rise else (1 + math.cos(math.pi * (ring - rise) / (1 - rise))) / 2
    return glow, ring


def _font(size):
    return demo.font(round(size * 1.35), 800)


def badge_size(label='LIVE', size=40):
    """The `(w, h)` a `draw_live_badge` of `label` at `size` takes up, for
    placing it (centring it, or tucking it into a corner)."""
    tw, th = vb.text.block_size([label], _font(size))
    pad = size * 0.55
    return pad + 0.64 * size + 0.45 * size + tw + pad, th + 1.4 * pad


def draw_live_badge(cv, x, y, t, label='LIVE', size=40, color=demo.ACCENT, ink=demo.INK,
                    panel='#1f2128', period=1.2, start=0.0):
    """Draw a live badge at time `t` from its top-left (x, y): a rounded
    panel holding a dot in `color` and `label`, the dot pulsing with
    `live_pulse` (brightening, swelling a little and casting a fading ring)
    and the label dimming slightly between beats. `size` is the label's
    cap height in pixels; everything else scales from it. Returns its Box."""
    glow, ring = live_pulse(t, period, start)
    f, r, pad, (w, h) = _font(size), size * 0.32, size * 0.55, badge_size(label, size)
    th = vb.text.block_size([label], f)[1]
    cv.shadow(x, y, w, h, radius=h * 0.3, dy=size * 0.12, blur=size * 0.5, color=(0, 0, 0, 0.4))
    cv.rect(x, y, w, h, panel, radius=h * 0.3)
    cv.outline(x, y, w, h, demo.LINE, width=max(1, size * 0.04), radius=h * 0.3)
    cx, cy = x + pad + r, y + h / 2
    if t >= start:
        cv.arc(cx, cy, r * (1 + 1.2 * ring), 0, 2 * math.pi, color, width=size * 0.06,
               alpha=0.7 * (1 - ring) ** 1.5)
    demo.dot(cv, cx, cy, r * (1.9 + 0.5 * glow), color=color, alpha=0.18 * glow)
    demo.dot(cv, cx, cy, r * (1 + 0.12 * glow), color=color, alpha=0.55 + 0.45 * glow)
    vb.text.draw(cv, [label], f, cx + r + size * 0.45, y + (h - th) / 2, ink, alpha=0.72 + 0.28 * glow)
    box = vb.Box(x, y, w, h)
    cv.mark('badge', *box)
    return box


def draw(n, cv):
    t = n / demo.FPS
    size = 72
    w, h = badge_size('LIVE', size)
    draw_live_badge(cv, (demo.W - w) / 2, (demo.H - h) / 2, t, size=size, period=1.0, start=0.3)


TECHNIQUE = Technique(
    id='live-indicator-pulse',
    name='Live indicator pulse',
    family='broadcast',
    group='Timers & indicators',
    aliases=('live badge', 'REC dot', 'on-air light', 'recording indicator'),
    definition='A little red dot next to a LIVE tag beats on and off at an even tempo, '
               'a faint ring rippling out from it, to signal that the broadcast is happening now.',
    phrasings=('put a blinking red LIVE badge in the corner',
               'show a pulsing recording dot so people know we are on air',
               'a throbbing red light next to the word live'),
    related=('pulse-loader', 'badge-count-bump', 'location-ripple-pulse', 'scale-pulse',
             'numbered-hotspot-pins', 'like-heart-burst'),
    api=('videobuilder.techniques.broadcast.live_indicator_pulse.draw_live_badge',
         'videobuilder.techniques.broadcast.live_indicator_pulse.live_pulse',
         'videobuilder.techniques.broadcast.live_indicator_pulse.badge_size'),
    demo=lambda: demo.film(draw),
)

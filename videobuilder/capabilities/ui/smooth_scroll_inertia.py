"""Smooth Scroll Inertia: the page doesn't jump with each wheel notch; it
chases the scroll target, gliding fast at first and easing to a stop after
the input ends, so stepped scrolling reads as one continuous drift."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def scroll_target(t, notches):
    """The raw scroll position at `t` seconds: the sum of every `(time, delta)`
    in `notches` that has happened by then (what the wheel asked for)."""
    return sum(d for ti, d in notches if t >= ti)


def smooth_scroll(t, notches, lag=0.18):
    """The smoothed scroll position at `t` seconds for wheel input `notches`,
    a sequence of `(time, delta)` steps. The content chases the raw target
    exponentially with time constant `lag` seconds (larger = floatier), so
    each step starts fast and eases out, and steps close together blend into
    one glide. Closed form, so any frame can be drawn on its own."""
    if lag <= 0:
        return scroll_target(t, notches)
    return sum(d * (1 - math.exp(-(t - ti) / lag)) for ti, d in notches if t >= ti)


STEP = 85
NOTCHES = tuple((t, STEP) for t in (0.35, 0.43, 0.51, 0.59)) + tuple((t, STEP) for t in (1.55, 1.63, 1.71))
ROW_H, GAP = 70, 13
COLORS = (demo.ACCENT, demo.TEAL, '#e6b84f', '#7d8cf0')


def _row(cv, x, y, w, i):
    cv.rect(x, y, w, ROW_H, demo.LINE, radius=9)
    demo.dot(cv, x + 35, y + ROW_H / 2, 19, color=COLORS[i % len(COLORS)])
    cv.rect(x + 65, y + 21, w * (0.55 - 0.08 * (i % 3)), 9, demo.INK, radius=4.5, alpha=0.9)
    cv.rect(x + 65, y + 39, w * (0.35 + 0.06 * (i % 2)), 8, demo.MUTED, radius=4, alpha=0.7)


def _mouse(cv, cx, cy, flash):
    cv.outline(cx - 22, cy - 35, 44, 70, demo.MUTED, width=2, radius=22)
    cv.rect(cx - 3.5, cy - 22, 7, 17, demo.ACCENT if flash else demo.MUTED, radius=3.5, alpha=0.5 + 0.5 * flash)
    for k in range(3):  # downward chevrons under the mouse while a notch is fresh
        y = cy + 50 + k * 13
        cv.line(cx - 9, y, cx, y + 7, demo.ACCENT, width=3, alpha=flash * (1 - 0.3 * k))
        cv.line(cx, y + 7, cx + 9, y, demo.ACCENT, width=3, alpha=flash * (1 - 0.3 * k))


def draw(n, cv):
    t = n / demo.FPS
    pos = smooth_scroll(t, NOTCHES)
    raw = scroll_target(t, NOTCHES)
    vx, vy, vw, vh = demo.W / 2 - 165, 45, 330, demo.H - 90
    cv.outline(vx - 3, vy - 3, vw + 6, vh + 6, demo.LINE, width=2, radius=15)
    with cv.clip(vx, vy, vw, vh, radius=12):
        first = int((pos - 10) // (ROW_H + GAP))
        for i in range(max(first, 0), first + 9):
            _row(cv, vx + 10, vy + 10 + i * (ROW_H + GAP) - pos, vw - 20, i)
    cv.mark('feed', vx, vy, vw, vh)

    # the scrollbar: a hollow marker jumps to where the wheel sent it, the filled thumb glides after it
    total = sum(d for _, d in NOTCHES)
    tx, th = vx + vw + 20, 80
    cv.rect(tx, vy, 6, vh, demo.LINE, radius=3)
    cv.outline(tx - 3, vy + (vh - th) * raw / total, 12, th, demo.MUTED, width=2, radius=6, alpha=0.8)
    cv.rect(tx, vy + (vh - th) * pos / total, 6, th, demo.INK, radius=3)

    flash = max((1 - (t - ti) / 0.2 for ti, _ in NOTCHES if 0 <= t - ti < 0.2), default=0.0)
    _mouse(cv, vx - 130, demo.H / 2 - 30, vb.clamp01(flash))


CAPABILITY = Capability(
    id='smooth-scroll-inertia',
    name='Smooth scroll inertia',
    family='ui',
    group='Scroll',
    aliases=('smooth scrolling', 'inertial scroll', 'lerp scroll', 'scroll smoothing'),
    definition='Each scroll input sets a target the page then chases, gliding quickly at first and '
               'easing gently to rest, so choppy wheel steps become one fluid motion.',
    phrasings=('make the page scroll smoothly instead of jumping a notch at a time',
               'the list should keep gliding a little after I stop scrolling',
               'buttery scrolling that eases to a stop'),
    related=('momentum-fling', 'bounce-ease-in', 'friction-deceleration', 'scroll-driven-text-reveal',
             'frame-stutter', 'rolling-shutter-wobble'),
    api=('videobuilder.capabilities.ui.smooth_scroll_inertia.smooth_scroll',
         'videobuilder.capabilities.ui.smooth_scroll_inertia.scroll_target'),
    demo=lambda: demo.film(draw),
)

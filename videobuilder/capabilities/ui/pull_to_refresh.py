"""Pull to refresh: a list is dragged down from its top, a spinner grows into
the gap it opens, keeps spinning after the release while the list rests a
little lower, then the list snaps back up with a new item on top."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def rubber_band(d, limit):
    """A drag of `d` px as the list actually moves: one-for-one at first, then
    stiffening so it never passes `limit`."""
    return limit * (1 - 1 / (1 + max(0.0, d) / limit))


def pull_to_refresh(t, grab=0.3, release=1.1, done=2.1, settle=0.35, drag=280, limit=200, rest=90):
    """The state of a pull to refresh at `t` seconds, as `(offset, pull, spin,
    fresh)`. The finger drags `drag` px from `grab` to `release` (the list
    follows through `rubber_band`, up to `limit`); on release the list eases to
    `rest` px down and the spinner turns until `done`, when the list closes over
    `settle` seconds. `offset` is how far the list sits down, `pull` 0 -> 1 how
    far the spinner has grown (1 once armed), `spin` the spinner's turn in
    radians, `fresh` 0 -> 1 the new content arriving after `done`."""
    held = vb.ease_in_out_quart(vb.clamp01((t - grab) / (release - grab)))
    peak = rubber_band(drag, limit)
    if t < release:
        offset = rubber_band(drag * held, limit)
    elif t < done:
        offset = rest + (peak - rest) * (1 - vb.ease_out_expo(vb.clamp01((t - release) / settle)))
    else:
        offset = rest * (1 - vb.ease_out_quint(vb.clamp01((t - done) / settle)))
    pull = vb.clamp01(offset / rest) if t < release else 1.0
    spin = 1.2 * pull + (2 * math.pi * 1.6 * (min(t, done) - release) if t > release else 0.0)
    fresh = vb.clamp01((t - done) / settle)
    return offset, pull, spin, fresh


def draw_spinner(cv, cx, cy, pull, spin, r=18, color=demo.ACCENT, width=5, alpha=1.0):
    """A refresh spinner centred at (cx, cy): an arc that grows from a dot to
    three quarters of a ring as `pull` goes 0 -> 1, turned by `spin` radians."""
    if pull <= 0 or alpha <= 0:
        return
    sweep = 0.15 + 1.35 * math.pi * pull
    start = -math.pi / 2 + spin
    cv.arc(cx, cy, r * (0.6 + 0.4 * pull), start, start + sweep, color, width=width, alpha=alpha * min(1, 2 * pull))


ROWS = 6


def _row(cv, x, y, w, h, i, accent=False):
    cv.rect(x, y, w, h, '#1d1f26', radius=9)
    cv.rect(x + 11, y + (h - 34) / 2, 34, 34, demo.TEAL if accent else '#2c2f38', radius=7)
    cv.rect(x + 58, y + h / 2 - 10, w * (0.42 - 0.05 * (i % 3)), 7, demo.INK, radius=3.5, alpha=0.85)
    cv.rect(x + 58, y + h / 2 + 4, w * (0.55 - 0.07 * (i % 2)), 6, demo.MUTED, radius=3, alpha=0.6)


def draw(n, cv):
    t = n / demo.FPS
    offset, pull, spin, fresh = pull_to_refresh(t)
    pw, ph = 380, 440
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.shadow(px, py, pw, ph, radius=24, dy=8, blur=26, color=(0, 0, 0, 0.5))
    cv.rect(px, py, pw, ph, '#16171d', radius=24)
    cv.outline(px, py, pw, ph, demo.LINE, width=2, radius=24)
    pad, rh, gap = 14, 56, 9
    with cv.clip(px, py, pw, ph, radius=24):
        draw_spinner(cv, demo.W / 2, py + (pad + offset) / 2 + 4, pull, spin, alpha=1 - fresh)
        top = py + pad + offset
        # The new item slides in on top of the list as it closes.
        if fresh > 0:
            top -= (rh + gap) * (1 - fresh)
            with cv.layer(opacity=fresh):
                _row(cv, px + pad, top, pw - 2 * pad, rh, 0, accent=True)
            top += rh + gap
        for i in range(ROWS):
            _row(cv, px + pad, top + i * (rh + gap), pw - 2 * pad, rh, i + 1)
    # The finger: presses on the list, drags it down, lets go.
    if 0.15 < t < 1.45:
        a = vb.clamp01(min((t - 0.15) / 0.15, (1.45 - t) / 0.3))
        fy = py + 150 + offset if t < 1.1 else py + 150 + rubber_band(280, 200) + 20 * (t - 1.1) / 0.35
        demo.dot(cv, demo.W / 2 + 80, fy, r=17, color=demo.INK, alpha=0.35 * a)
        cv.arc(demo.W / 2 + 80, fy, 17, 0, 2 * math.pi, demo.INK, width=2, alpha=0.8 * a)
    cv.mark('list', px, py, pw, ph)


TECHNIQUE = Technique(
    id='pull-to-refresh',
    name='Pull to refresh',
    family='ui',
    group='Gestures & drag',
    aliases=('overscroll refresh', 'drag to refresh', 'swipe to refresh'),
    definition='Dragging a list down from its top opens a gap where a spinner grows and turns, '
               'then the list springs back up with fresh items.',
    phrasings=('pull the feed down so a loading spinner appears and new posts come in',
               'drag the list down to reload it, like on a phone app',
               'the list stretches down, a spinner spins, then it snaps back updated'),
    related=('infinite-scroll-append', 'scroll-progress-bar', 'fade-up-scroll-reveal', 'scroll-pin-section',
             'sorted-bar-reorder', 'roll-up'),
    api=('videobuilder.techniques.ui.pull_to_refresh.pull_to_refresh',
         'videobuilder.techniques.ui.pull_to_refresh.draw_spinner',
         'videobuilder.techniques.ui.pull_to_refresh.rubber_band'),
    demo=lambda: demo.film(draw),
)

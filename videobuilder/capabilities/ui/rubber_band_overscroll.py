"""Rubber band overscroll: a scrolled list dragged past its end gives way less
and less the further it is pulled, then springs back to its edge when let go."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rubber_band(overscroll, limit, resistance=0.55):
    """How far content moves when dragged `overscroll` px past its edge, in a
    view `limit` px long: almost 1:1 at first, then stiffer and stiffer,
    never reaching `limit`. Sign follows `overscroll`. `resistance` (0..1)
    sets how soon it stiffens; 0.55 is the familiar phone feel."""
    if limit <= 0:
        return 0.0
    d = abs(overscroll)
    out = (1 - 1 / (d * resistance / limit + 1)) * limit
    return math.copysign(out, overscroll)


def overscroll_release(offset, t, hz=2.2, ratio=0.85):
    """The offset `t` seconds after content held `offset` px past its edge is
    let go: a quick spring back to 0 (`ratio` below 1 lets it just kiss past
    the edge and settle)."""
    if t <= 0:
        return offset
    return offset * (1 - vb.spring(t, **vb.damped(ratio, hz)))


PANEL_W, PANEL_H = 300, 380
ROW_H, GAP, PAD = 52, 10, 14
PULL = 230                      # how far the finger travels past the top
GRAB, LET_GO = (0.4, 1.6), 1.85  # seconds: drag, then release


def _list(cv, x, y, offset):
    swatches = ('#f2b632', '#8a8cf6', '#8a8cf6', '#f2b632', '#8a8cf6', '#8a8cf6', '#f2b632')
    with cv.clip(x, y, PANEL_W, PANEL_H, radius=16):
        for i, c in enumerate(swatches):
            ry = y + PAD + offset + i * (ROW_H + GAP)
            rx, rw = x + PAD, PANEL_W - 2 * PAD - 12
            cv.rect(rx, ry, rw, ROW_H, '#1f2128', radius=10)
            cv.rect(rx + 10, ry + 12, 28, 28, c, radius=7)
            cv.rect(rx + 50, ry + 15, rw * 0.55, 7, demo.INK, radius=3.5, alpha=0.8)
            cv.rect(rx + 50, ry + 30, rw * 0.32, 6, demo.MUTED, radius=3, alpha=0.7)
    # the scrollbar squeezes shorter while the list is pulled past its end
    bar = 110 * (1 - 0.5 * min(1, offset / 120))
    cv.rect(x + PANEL_W - 12, y + 10, 4, bar, demo.MUTED, radius=2, alpha=0.8)


def draw(n, cv):
    t = n / demo.FPS
    x, y = demo.W / 2 - PANEL_W / 2, demo.H / 2 - PANEL_H / 2
    held = rubber_band(PULL, PANEL_H)
    if t < LET_GO:
        drag = PULL * vb.ease_in_out_quart(demo.phase(n, *GRAB))
        offset = rubber_band(drag, PANEL_H)
    else:
        drag = PULL
        offset = overscroll_release(held, t - LET_GO)
    cv.shadow(x, y, PANEL_W, PANEL_H, radius=16, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(x, y, PANEL_W, PANEL_H, '#191a20', radius=16)
    cv.outline(x, y, PANEL_W, PANEL_H, demo.LINE, width=2, radius=16)
    _list(cv, x, y, offset)
    cv.mark('list', x, y + offset, PANEL_W, PANEL_H)
    # the finger: pulls further than the list follows, then lifts off
    fx, fy = x + PANEL_W * 0.62, y + 70 + drag
    lift = vb.clamp01((t - LET_GO) / 0.25)
    if lift < 1:
        demo.dot(cv, fx, fy, 22, color=demo.INK, alpha=0.18 * (1 - lift))
        cv.arc(fx, fy, 22, 0, 2 * math.pi, demo.INK, width=3, alpha=0.9 * (1 - lift))


CAPABILITY = Capability(
    id='rubber-band-overscroll',
    name='Rubber band overscroll',
    family='ui',
    group='Gestures & drag',
    aliases=('elastic bounds', 'overscroll stretch', 'rubber banding', 'bounce scroll'),
    definition='A list dragged beyond its first or last item follows the finger more and more grudgingly, '
               'then snaps back to its edge as soon as it is let go.',
    phrasings=('the list stretches when you pull past the top and bounces back',
               'scrolling past the end gives a springy resistance',
               'pull down on the feed and it rubber-bands back into place'),
    related=('elastic-stretch', 'rubber-band-snap', 'elastic-ease-out', 'squash-on-tap',
             'offset-path-expansion', 'elastic-horizontal-squash'),
    api=('videobuilder.capabilities.ui.rubber_band_overscroll.rubber_band',
         'videobuilder.capabilities.ui.rubber_band_overscroll.overscroll_release'),
    demo=lambda: demo.film(draw),
)

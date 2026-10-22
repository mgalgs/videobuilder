"""Timeline scroll: a dated axis slides sideways under a fixed marker,
stopping on each milestone in turn so its year and caption take focus
before the line moves on to the next."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def timeline_stops(p, count, dwell=0.35, ease=vb.ease_in_out_quart):
    """Where a stepped timeline is at progress `p` (0 -> 1) across `count`
    stops: a float index, 0 at the first stop and `count - 1` at the last.
    Each of the `count - 1` legs holds still for its first `dwell` share,
    then eases to the next stop, so the line rests on stop 0 at the start and
    arrives on the last stop exactly at `p = 1`."""
    if count < 2:
        return 0.0
    legs = count - 1
    t = vb.clamp01(p) * legs
    leg = min(int(t), legs - 1)
    local = t - leg
    move = 0.0 if local <= dwell else ease((local - dwell) / (1 - dwell)) if dwell < 1 else 1.0
    return leg + move


def focus(position, i, falloff=1.0):
    """How strongly stop `i` is in focus (1 on the marker, 0 at `falloff`
    stops away or more) when the timeline is at float index `position`."""
    return vb.clamp01(1 - abs(position - i) / falloff)


def draw_timeline(cv, events, position, marker_x, y, spacing, card, x=0, w=None,
                  color=demo.MUTED, accent=demo.ACCENT, ticks=4):
    """A horizontal timeline at height `y`, scrolled so float index `position`
    sits under the fixed marker at `marker_x`, clipped to the band from `x`
    `w` wide (default the canvas width). `events` are the stops, `spacing`
    pixels apart, with `ticks` minor ticks between each pair.
    `card(cv, i, event, ex, y, f)` draws stop `i` at axis x `ex` with focus
    `f` (0 -> 1); stops wholly off the band are skipped."""
    w = cv.width - x if w is None else w
    left = marker_x - position * spacing
    with cv.clip(x, y - cv.height, w, 2 * cv.height):
        cv.line(x, y, x + w, y, color, width=3, alpha=0.7)
        first, last = math.floor((x - left) / spacing) - 1, math.ceil((x + w - left) / spacing) + 1
        for k in range(first, last + 1):
            for m in range(1, ticks + 1):
                tx = left + (k + m / (ticks + 1)) * spacing
                cv.line(tx, y - 6, tx, y + 6, color, width=2, alpha=0.45)
        for i, ev in enumerate(events):
            ex = left + i * spacing
            if x - spacing <= ex <= x + w + spacing:
                f = focus(position, i)
                cv.line(ex, y - 14, ex, y + 14, color, width=3)
                demo.dot(cv, ex, y, 10 + 8 * f, accent if f > 0.5 else color, alpha=0.6 + 0.4 * f)
                card(cv, i, ev, ex, y, f)


# ---- demo ----

EVENTS = (('1969', 'First landing'), ('1981', 'Shuttle flies'), ('1998', 'Station assembly'),
          ('2012', 'Rover touchdown'), ('2021', 'Helicopter hop'))
AXIS_Y = demo.H * 0.56
SPACING = 290
MARKER_X = demo.W / 2


def _card(cv, i, event, ex, y, f):
    year, caption = event
    up = i % 2 == 0
    cw, ch = 210, 84
    lift = 14 * f
    cy = (y - 40 - ch - lift) if up else (y + 40 + lift)
    stem0, stem1 = (y - 16, cy + ch) if up else (y + 16, cy)
    cv.line(ex, stem0, ex, stem1, demo.LINE, width=2)
    with cv.layer(opacity=0.45 + 0.55 * f):
        cv.shadow(ex - cw / 2, cy, cw, ch, radius=12, dy=6, blur=18, color=(0, 0, 0, 0.4))
        cv.rect(ex - cw / 2, cy, cw, ch, '#1f2128', radius=12)
        cv.outline(ex - cw / 2, cy, cw, ch, demo.ACCENT if f > 0.5 else demo.LINE, width=2, radius=12)
        demo.word(cv, year, ex, cy + 32, size=34, color=demo.ACCENT if f > 0.5 else demo.INK)
        demo.word(cv, caption, ex, cy + 64, size=18, color=demo.MUTED, weight=600)
    cv.mark(f'event{i}', ex - cw / 2, cy, cw, ch)


def draw(n, cv):
    pos = timeline_stops(demo.phase(n, 0.2, 2.8), len(EVENTS))
    # the fixed marker: a playhead the line slides under, behind the cards
    top, bottom = 100, demo.H - 36
    cv.line(MARKER_X, top, MARKER_X, bottom, demo.ACCENT, width=2, alpha=0.35)
    for yy in (top, bottom):
        demo.dot(cv, MARKER_X, yy, 6)
    draw_timeline(cv, EVENTS, pos, MARKER_X, AXIS_Y, SPACING, _card)
    # edge fades so the line runs off into the background
    for k in range(12):
        a = (1 - k / 12) ** 2
        cv.rect(k * 10, 0, 10, demo.H, demo.BG, alpha=a)
        cv.rect(demo.W - (k + 1) * 10, 0, 10, demo.H, demo.BG, alpha=a)
    demo.word(cv, 'Milestones', demo.W / 2, 52, size=30, color=demo.INK)
    cv.mark('marker', MARKER_X - 6, top - 6, 12, bottom - top + 12)


TECHNIQUE = Technique(
    id='timeline-scroll',
    name='Timeline scroll',
    family='broadcast',
    group='Charts',
    aliases=('scrolling timeline', 'history timeline', 'horizontal timeline', 'chronology scroll'),
    definition='A dated line slides sideways beneath a fixed marker, pausing on each milestone so its '
               'date and label light up before the line travels on to the next one.',
    phrasings=('walk through the years along a line that slides past',
               'a history of key dates, stopping on each one as the timeline moves',
               'pan along a timeline from the first event to the latest'),
    related=('horizontal-scroll-section', 'scroll-scrubbed-frame-sequence', 'scrollytelling-step-sequence',
             'scroll-snap-sections', 'roll-up', 'hyperlapse'),
    api=('videobuilder.techniques.broadcast.timeline_scroll.draw_timeline',
         'videobuilder.techniques.broadcast.timeline_scroll.timeline_stops',
         'videobuilder.techniques.broadcast.timeline_scroll.focus'),
    demo=lambda: demo.film(draw),
)

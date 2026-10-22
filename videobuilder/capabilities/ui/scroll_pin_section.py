"""Scroll pin section: while a page scrolls, one section catches on the top
of the viewport and holds there, its own content stepping on as the scroll
continues, until the pinned stretch runs out and it scrolls away with the rest."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def scroll_pin(scroll, top, length, at=0.0):
    """Where a pinned section sits for page scroll `scroll` (px).

    The section starts at `top` in page coordinates and pins once its top
    reaches `at` px below the viewport's top edge; it stays there for the
    next `length` px of scroll, then moves off with the page. Returns
    `(y, p)`: the section's top in viewport coordinates and its progress
    0 -> 1 through the pinned stretch (drive the section's content with `p`).
    Everything after the section in the page should sit `length` px further
    down, the room the pin takes up."""
    held = min(max(scroll - (top - at), 0.0), length)
    return top - scroll + held, held / length if length > 0 else float(scroll >= top - at)


# The demo: a browser-ish window whose page scrolls steadily from start to end.
WIN = vb.Box(150, 34, 660, 472)
BAR = 34                          # the window's title bar
VIEW = vb.Box(WIN.x, WIN.y + BAR, WIN.w - 26, WIN.h - BAR)  # the page viewport, scrollbar to its right
INTRO = 150                       # page px above the section
GAP = 16                          # the section's inset inside the viewport
SEC_H = VIEW.h - 2 * GAP
PIN = 700                         # scroll px the section stays pinned for
END = INTRO - GAP + PIN + 250     # total scroll across the demo
PAGE_H = INTRO + SEC_H + PIN + 420


def _bars(cv, x, y, widths, alpha=0.5):
    for i, w in enumerate(widths):
        cv.rect(x, y + i * 18, w, 7, demo.MUTED, radius=3.5, alpha=alpha)


def _section(cv, x, y, w, h, p):
    """The pinned panel: three tab marks fill in turn, and one dot splits into four."""
    cv.shadow(x, y, w, h, radius=14, dy=8, blur=24, color=(0, 0, 0, 0.4))
    cv.rect(x, y, w, h, '#1d1f26', radius=14)
    tab_w = (w - 80) / 3
    for i in range(3):
        tx = x + 32 + i * (tab_w + 8)
        cv.rect(tx, y + 26, tab_w, 4, demo.LINE, radius=2)
        fill = vb.clamp01(p * 3 - i)
        if fill > 0:
            cv.rect(tx, y + 26, tab_w * fill, 4, demo.ACCENT, radius=2)
    cx, cy = x + w / 2, y + h * 0.46
    split = vb.ease_in_out_quart(vb.clamp01((p - 0.3) / 0.45))
    if split <= 0:
        demo.dot(cv, cx, cy, 40, color=demo.TEAL)
    else:
        spread = 78 * split
        for k in range(4):
            a = k * math.pi / 2 - math.pi / 2
            demo.dot(cv, cx + spread * math.cos(a), cy + spread * math.sin(a), 40 - 14 * split,
                     color=demo.ACCENT if k % 2 == 0 else demo.TEAL)
    _bars(cv, x + w / 2 - 130, y + h - 70, (260, 170))
    cv.mark('section', x, y, w, h)


def draw(n, cv):
    t = demo.phase(n, 0.1, 2.9)  # a steady scroll, so only the pin explains the section holding still
    scroll = END * t
    cv.shadow(WIN.x, WIN.y, WIN.w, WIN.h, radius=12, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(WIN.x, WIN.y, WIN.w, WIN.h, '#17181e', radius=12)
    with cv.clip(VIEW.x, VIEW.y, VIEW.w, VIEW.h):
        top = VIEW.y - scroll    # page y=0 on screen
        # the rest of the page: intro copy, a ruler down the side, copy after the pin
        _bars(cv, VIEW.x + 32, top + 36, (300, 300, 260, 180))
        for k in range(0, PAGE_H, 60):
            cv.line(VIEW.x + VIEW.w - 30, top + k, VIEW.x + VIEW.w - 18, top + k, demo.MUTED, width=2, alpha=0.4)
        after = top + INTRO + SEC_H + PIN + 40
        _bars(cv, VIEW.x + 32, after, (320, 320, 280, 200))
        _bars(cv, VIEW.x + 32, after + 110, (320, 240))
        y, p = scroll_pin(scroll, INTRO, PIN, at=GAP)
        _section(cv, VIEW.x + 24, VIEW.y + y, VIEW.w - 70, SEC_H, p)
    # title bar, then the scrollbar, which keeps moving while the section holds still
    with cv.clip(WIN.x, WIN.y, WIN.w, BAR, radius=0):
        cv.rect(WIN.x, WIN.y, WIN.w, BAR + 12, '#202229', radius=12)
    cv.line(WIN.x, WIN.y + BAR, WIN.x + WIN.w, WIN.y + BAR, demo.LINE, width=1)
    cv.rect(WIN.x + 16, WIN.y + 10, 14, 14, demo.ACCENT, radius=3)
    for i in range(3):
        cv.rect(WIN.x + WIN.w - 116 + i * 34, WIN.y + 16, 24, 3, demo.MUTED, radius=1.5)
    track_x, track_h = WIN.x + WIN.w - 16, VIEW.h - 16
    thumb_h = track_h * VIEW.h / PAGE_H
    thumb_y = VIEW.y + 8 + (track_h - thumb_h) * scroll / (PAGE_H - VIEW.h)
    cv.rect(track_x, VIEW.y + 8, 5, track_h, demo.LINE, radius=2.5)
    cv.rect(track_x, thumb_y, 5, thumb_h, demo.TEAL, radius=2.5)
    cv.mark('scrollbar', track_x, thumb_y, 5, thumb_h)


CAPABILITY = Capability(
    id='scroll-pin-section',
    name='Scroll pin section',
    family='ui',
    group='Scroll',
    aliases=('sticky section', 'pinned scene', 'scroll pinning'),
    definition='As the page scrolls, one section locks in place on screen and plays out its own '
               'animation for a while, then lets go and scrolls off with everything else.',
    phrasings=('the panel sticks to the top while you keep scrolling and its contents change',
               'freeze this part of the page on screen and animate it as the user scrolls',
               'a sticky block that steps through its content before the page moves on'),
    related=('roll-up', 'timeline-scroll', 'scroll-driven-text-reveal', 'infinite-scroll-append', 'uncover',
             'skeleton-shimmer'),
    api=('videobuilder.capabilities.ui.scroll_pin_section.scroll_pin',),
    demo=lambda: demo.film(draw),
)

"""Horizontal Scroll Section: a page scrolls down until one section fills the
view, the section pins, and further scrolling slides its row of panels
sideways instead; once the row is spent the page carries on downward."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def track_travel(count, panel_w, gap, view_w, pad=0):
    """How far a row of `count` panels `panel_w` wide, `gap` apart, with `pad`
    at each end, must slide to bring its last panel into a `view_w` view."""
    return max(0.0, count * panel_w + (count - 1) * gap + 2 * pad - view_w)


def horizontal_scroll(s, pin_at, travel, length=None):
    """Where things sit at vertical page scroll `s` (pixels) for a section that
    pins when `s` reaches `pin_at` and stays pinned for `length` pixels of
    scrolling (default `travel`: one pixel sideways per pixel down). Returns
    `(page_y, track_x)`: how far the page has moved up, and how far the
    section's row has moved left (0 -> `travel`)."""
    length = travel if length is None else length
    if s <= pin_at:
        return s, 0.0
    if s >= pin_at + length:
        return s - length, float(travel)
    return pin_at, travel * (s - pin_at) / length if length else float(travel)


def draw_track(cv, x, y, w, h, panel, count, panel_w, gap, track_x, pad=0):
    """A sideways row clipped to the section box (x, y, w, h), slid left by
    `track_x`. `panel(cv, i, px, py, pw, ph)` draws panel `i`; panels wholly
    outside the box are skipped."""
    with cv.clip(x, y, w, h):
        for i in range(count):
            px = x + pad + i * (panel_w + gap) - track_x
            if px + panel_w >= x and px <= x + w:
                panel(cv, i, px, y, panel_w, h)


# ---- demo ----

WIN_W, WIN_H, BAR = 820, 470, 30
WIN_X, WIN_Y = (demo.W - WIN_W) / 2, (demo.H - WIN_H) / 2
VX, VY, VW, VH = WIN_X, WIN_Y + BAR, WIN_W, WIN_H - BAR     # the page viewport
COUNT, PANEL_W, GAP, PAD = 5, 300, 24, 36
PANEL_Y, PANEL_H = 64, 300                                   # within the pinned section
HERO, FOOTER = 150, 120                                      # page above and below the section
TRAVEL = track_travel(COUNT, PANEL_W, GAP, VW, PAD)
TOTAL = HERO + TRAVEL + FOOTER                               # the page's whole scroll range
PANEL_BG = '#1f2128'


def _lines(cv, x, y, widths, color=demo.MUTED, alpha=0.6):
    for k, lw in enumerate(widths):
        cv.rect(x, y + k * 14, lw, 5, color, radius=2.5, alpha=alpha)


def _panel(cv, i, x, y, w, h):
    cv.rect(x, y, w, h, PANEL_BG, radius=14)
    cv.outline(x, y, w, h, demo.LINE, width=1.5, radius=14)
    color = (demo.ACCENT, demo.TEAL)[i % 2]
    cx, cy = x + w / 2, y + h * 0.4
    kind = i % 4
    if kind == 0:
        cv.arc(cx, cy, 46, 0, 2 * math.pi, color, width=22)
    elif kind == 1:
        for k in (-1, 0, 1):
            cv.rect(cx + k * 36 - 13, cy - 44, 26, 88, color, radius=13)
    elif kind == 2:
        cv.sector(cx, cy + 8, 62, math.pi, 2 * math.pi, color)
    else:
        cv.rect(cx - 52, cy - 52, 104, 104, color, radius=22)
    f = demo.mono(15, 700)
    vb.text.draw(cv, [f'0{i + 1}'], f, x + 20, y + 16, demo.MUTED)
    _lines(cv, x + 24, y + h - 64, (w * 0.62, w * 0.5, w * 0.36))


def _page(cv, page_y, track_x):
    top = VY - page_y
    # the hero above the section
    vb.text.draw(cv, ['Scroll down'], demo.font(40, 800), VX + 40, top + 34, demo.INK)
    _lines(cv, VX + 42, top + 98, (300, 220))
    # the section: it pins to the top of the view while its row slides
    sy = top + HERO
    vb.text.draw(cv, ['Featured'], demo.font(22, 800), VX + PAD, sy + 22, demo.INK)
    draw_track(cv, VX, sy + PANEL_Y, VW, PANEL_H, _panel, COUNT, PANEL_W, GAP, track_x, PAD)
    cv.mark('track', VX, sy + PANEL_Y, VW, PANEL_H)
    lit = round(track_x / TRAVEL * (COUNT - 1)) if TRAVEL else 0
    for k in range(COUNT):
        demo.dot(cv, VX + VW / 2 + (k - (COUNT - 1) / 2) * 18, sy + PANEL_Y + PANEL_H + 34, 4,
                 demo.ACCENT if k == lit else demo.MUTED, alpha=1 if k == lit else 0.5)
    # the page below the section
    fy = sy + VH
    cv.line(VX + 40, fy, VX + VW - 40, fy, demo.LINE, width=1.5)
    _lines(cv, VX + 40, fy + 30, (420, 360, 260))


def draw(n, cv):
    p = demo.phase(n, 0.25, 2.75)
    s = TOTAL * p * p * (3 - 2 * p)
    page_y, track_x = horizontal_scroll(s, HERO, TRAVEL)
    cv.shadow(WIN_X, WIN_Y, WIN_W, WIN_H, radius=14, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(WIN_X, WIN_Y, WIN_W, WIN_H, '#17181e', radius=14)
    with cv.clip(VX, VY, VW, VH):
        _page(cv, page_y, track_x)
    # browser bar
    with cv.clip(WIN_X, WIN_Y, WIN_W, BAR + 14, radius=14):
        cv.rect(WIN_X, WIN_Y, WIN_W, BAR, '#1c1d24')
    for k, c in enumerate(('#ef5b4c', '#e8b44a', '#4fc3b0')):
        demo.dot(cv, WIN_X + 18 + k * 16, WIN_Y + BAR / 2, 4.5, c, alpha=0.8)
    cv.line(WIN_X, VY, WIN_X + WIN_W, VY, demo.LINE, width=1)
    cv.outline(WIN_X, WIN_Y, WIN_W, WIN_H, demo.LINE, width=1.5, radius=14)
    # the vertical scrollbar: it keeps moving down the whole time
    tx, ty, th = VX + VW - 9, VY + 8, VH - 16
    thumb = th * VH / (VH + TOTAL)
    cv.rect(tx, ty, 4, th, demo.LINE, radius=2)
    cv.rect(tx, ty + (th - thumb) * (s / TOTAL), 4, thumb, demo.ACCENT, radius=2)
    cv.mark('page', VX, VY, VW, VH)


TECHNIQUE = Technique(
    id='horizontal-scroll-section',
    name='Horizontal scroll section',
    family='ui',
    group='Scroll',
    aliases=('scroll to horizontal', 'sideways scroll section', 'pinned horizontal scroll'),
    definition='A section locks in place as the page is scrolled down, and the downward scrolling '
               'slides its row of panels sideways until the row runs out and the page moves on.',
    phrasings=('scrolling down makes the cards move left instead of up',
               'the page sticks on a row of panels and slides through them sideways as you scroll',
               'a sideways gallery driven by the normal vertical scroll'),
    related=('timeline-scroll', 'roll-up', 'rolling-end-credits', 'pan', 'scroll-driven-text-reveal', 'tilt'),
    api=('videobuilder.techniques.ui.horizontal_scroll_section.horizontal_scroll',
         'videobuilder.techniques.ui.horizontal_scroll_section.track_travel',
         'videobuilder.techniques.ui.horizontal_scroll_section.draw_track'),
    demo=lambda: demo.film(draw),
)

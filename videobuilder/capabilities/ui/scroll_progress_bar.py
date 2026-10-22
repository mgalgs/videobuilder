"""Scroll progress bar: a thin bar pinned along the top of a page fills from
left to right in step with how far the page has been scrolled."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def scroll_progress(offset, content_h, view_h):
    """How far through a page the reader is, 0 -> 1: `offset` px scrolled of
    a page `content_h` tall seen through a viewport `view_h` tall. A page that
    fits the viewport counts as fully read."""
    room = content_h - view_h
    return 1.0 if room <= 0 else vb.clamp01(offset / room)


def draw_scroll_progress_bar(cv, x, y, w, p, color, height=8, track=None, track_alpha=0.25, radius=None):
    """Draw the bar at progress `p` (0 -> 1): a `w`-wide `track` strip (none
    when `track` is None) from (x, y), filled with `color` from the left to
    `p` of its width. Drive `p` with `scroll_progress` so it tracks the page.
    `radius` rounds the fill's ends (default: square, as it hugs an edge).
    Returns the Box of the filled part."""
    r = 0 if radius is None else radius
    if track is not None:
        cv.rect(x, y, w, height, track, radius=r, alpha=track_alpha)
    fw = w * vb.clamp01(p)
    if fw > 0:
        cv.rect(x, y, fw, height, color, radius=min(r, fw / 2))
    return vb.Box(x, y, fw, height)


# The demo: a browser-like window over a long article that scrolls by itself.
WIN_W, WIN_H = 720, 440
BAR_H = 40          # the window's header strip
CONTENT_H = 1340    # the article's full height, as `_article` lays it out


def _article(cv, x, y, w):
    """A long page of placeholder content from its top-left (x, y)."""
    cy = y + 28
    for block in range(6):
        cv.rect(x + 36, cy, w * 0.4, 12, demo.INK, radius=6, alpha=0.9)  # heading
        cy += 34
        if block % 2 == 0:
            cv.rect(x + 36, cy, w - 72, 126, demo.LINE, radius=10)  # an image
            demo.dot(cv, x + w / 2, cy + 63, r=34, color=demo.TEAL)
            cy += 150
        for line in range(5):
            cv.rect(x + 36, cy, (w - 72) * (0.6 if line == 4 else 1.0), 7, demo.MUTED, radius=3.5, alpha=0.7)
            cy += 16
        cy += 28


def draw(n, cv):
    x, y = (demo.W - WIN_W) / 2, (demo.H - WIN_H) / 2
    view_h = WIN_H - BAR_H
    # three flicks of the wheel with short reads between, as a reader scrolls
    offset = (CONTENT_H - view_h) * vb.interpolate(n / demo.FPS, (0.3, 0.9, 1.2, 1.8, 2.1, 2.7),
                                                   (0, 0.35, 0.35, 0.7, 0.7, 1), ease=vb.ease_out_quint)
    cv.shadow(x, y, WIN_W, WIN_H, radius=14, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(x, y, WIN_W, WIN_H, demo.BG, radius=14)
    with cv.clip(x, y + BAR_H, WIN_W, view_h):
        _article(cv, x, y + BAR_H - offset, WIN_W)
    with cv.clip(x, y, WIN_W, WIN_H, radius=14):
        cv.rect(x, y, WIN_W, BAR_H, demo.LINE)
        for i in range(3):
            demo.dot(cv, x + 22 + i * 18, y + BAR_H / 2, r=5, color=demo.MUTED)
        p = scroll_progress(offset, CONTENT_H, view_h)
        box = draw_scroll_progress_bar(cv, x, y + BAR_H - 8, WIN_W, p, demo.ACCENT, height=8,
                                       track=demo.MUTED, track_alpha=0.2)
    cv.outline(x, y, WIN_W, WIN_H, demo.LINE, width=2, radius=14)
    if box.w > 0:
        cv.mark('bar', *box)


TECHNIQUE = Technique(
    id='scroll-progress-bar',
    name='Scroll progress bar',
    family='ui',
    group='Scroll',
    aliases=('reading progress bar', 'scroll-linked progress', 'reading indicator'),
    definition='A slim strip along the top edge of a page grows from left to right as the page scrolls, '
               'reaching full width at the bottom.',
    phrasings=('a bar at the top that fills up as you scroll down the article',
               'show how far through the page the reader is with a line across the top',
               'a reading progress line that tracks the scroll'),
    related=('percentage-fill-bar', 'timeline-scroll', 'scroll-driven-text-reveal', 'news-ticker-crawl',
             'indeterminate-bar', 'striped-progress-bar'),
    api=('videobuilder.techniques.ui.scroll_progress_bar.draw_scroll_progress_bar',
         'videobuilder.techniques.ui.scroll_progress_bar.scroll_progress'),
    demo=lambda: demo.film(draw),
)

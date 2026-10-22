"""Scrollspy Nav Indicator: a side nav beside a scrolling page, whose
highlight slides to whichever section is in view as the page scrolls."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def scrollspy(scroll, tops, line=0.0, travel=0.0, ease=vb.ease_in_out_quart):
    """Which section is in view, as a float index for the indicator. Section
    `i` starts `tops[i]` px down the page (ascending, `tops[0]` usually 0);
    it becomes active once it crosses a reading `line` that far below the top
    of the viewport, at `scroll` px scrolled. With `travel` 0 the result is a
    whole index that jumps; with `travel` > 0 the indicator glides to the next
    item over that many px of scroll, centred on the crossing, eased by `ease`.
    Round it for the active item; draw the indicator at it."""
    at = scroll + line
    if travel <= 0:
        return float(sum(1 for t in tops[1:] if at >= t))
    return sum(ease(vb.clamp01((at - t) / travel + 0.5)) for t in tops[1:])


def draw_scrollspy_nav(cv, labels, x, y, w, row_h, at, font, ink=demo.INK, muted=demo.MUTED,
                       accent=demo.ACCENT, pill='#262a35'):
    """A vertical nav of `labels` from its top-left (x, y), `w` wide, one row
    every `row_h` px, with the indicator (a rounded pill and an `accent` bar
    on its left edge) at float index `at`, as `scrollspy` returns. Each label
    brightens from `muted` to `ink` as the indicator reaches it. Returns the
    Box of the indicator."""
    pad = row_h * 0.12
    py = y + at * row_h + pad
    ph = row_h - 2 * pad
    cv.rect(x, py, w, ph, pill, radius=ph * 0.22)
    cv.rect(x, py + ph * 0.2, 4, ph * 0.6, accent, radius=2)
    _, th = vb.text.block_size(['Ag'], font)
    for i, label in enumerate(labels):
        ty = y + i * row_h + (row_h - th) / 2
        lit = vb.clamp01(1 - abs(at - i))
        vb.text.draw(cv, [label], font, x + 18, ty, muted)
        if lit > 0:
            vb.text.draw(cv, [label], font, x + 18, ty, ink, alpha=lit)
    return vb.Box(x, py, w, ph)


LABELS = ('Overview', 'Motion', 'Rhythm', 'Flow')
COLORS = (demo.ACCENT, demo.TEAL, '#f2b33d', '#8a7cf0')
SECTION = 330                                   # px of page per section
PANEL = vb.Box(130, 60, 700, 420)
NAV_X, NAV_W, ROW = 150, 150, 46
PAGE = vb.Box(330, 70, 460, 400)                # the scrolling viewport
STOPS = (0.0, 0.35, 0.85, 1.2, 1.7, 2.05, 2.55)  # seconds: hold, scroll, hold, ...


def _section(cv, i, top, color):
    vb.text.draw(cv, [LABELS[i]], demo.font(34, 800), PAGE.x + 10, top + 14, demo.INK)
    for k, frac in enumerate((0.95, 0.8, 0.88)):
        cv.rect(PAGE.x + 10, top + 70 + k * 16, (PAGE.w - 40) * frac, 7, demo.LINE, radius=3.5)
    cx, cy, cw, ch = PAGE.x + 10, top + 130, PAGE.w - 40, 150
    cv.rect(cx, cy, cw, ch, '#1e2028', radius=14)
    for k, v in enumerate((0.45, 0.75, 0.6, 0.9, 0.35, 0.55)):
        bh = (ch - 30) * (v if i % 2 == 0 else 1.25 - v)
        cv.rect(cx + 30 + k * 66, cy + ch - 15 - bh, 34, bh, color, radius=10)


def draw(n, cv):
    t = n / demo.FPS
    ys = [0, 0, SECTION, SECTION, 2 * SECTION, 2 * SECTION, 3 * SECTION]
    scroll = vb.interpolate(t, STOPS, ys, ease=vb.ease_in_out_quart)
    cv.shadow(*PANEL, radius=20, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(*PANEL, '#1a1c22', radius=20)
    cv.line(PANEL.x + 180, PANEL.y + 18, PANEL.x + 180, PANEL.y + PANEL.h - 18, demo.LINE, width=2)
    at = scrollspy(scroll, [i * SECTION for i in range(len(LABELS))], line=SECTION / 2, travel=SECTION * 0.4)
    box = draw_scrollspy_nav(cv, LABELS, NAV_X, PANEL.y + 40, NAV_W, ROW, at, demo.font(18, 600))
    cv.mark('indicator', *box)
    with cv.clip(*PAGE):
        for i, color in enumerate(COLORS):
            _section(cv, i, PAGE.y + i * SECTION - scroll, color)
    track = PAGE.h - 20
    thumb = track * PAGE.h / (SECTION * (len(LABELS) - 1) + PAGE.h)
    ty = PAGE.y + 10 + (track - thumb) * scroll / (SECTION * (len(LABELS) - 1))
    cv.rect(PANEL.x + PANEL.w - 22, PAGE.y + 10, 4, track, demo.LINE, radius=2)
    cv.rect(PANEL.x + PANEL.w - 23, ty, 6, thumb, demo.MUTED, radius=3)


TECHNIQUE = Technique(
    id='scrollspy-nav-indicator',
    name='Scrollspy nav indicator',
    family='ui',
    group='Scroll',
    aliases=('scrollspy', 'active section highlight', 'table of contents tracking'),
    definition='As a page scrolls past its sections, the matching entry in a side menu lights up '
               'and a highlight slides along the menu to sit on it.',
    phrasings=('the sidebar menu follows along and highlights whichever part of the page you are reading',
               'a table of contents whose marker moves down as you scroll through the sections',
               'scroll the article and the nav pill jumps to the current heading'),
    related=('scroll-driven-text-reveal', 'scrolling-led-marquee-text', 'infinite-scroll-append',
             'border-glow-follow', 'timeline-scroll', 'roll-up'),
    api=('videobuilder.techniques.ui.scrollspy_nav_indicator.scrollspy',
         'videobuilder.techniques.ui.scrollspy_nav_indicator.draw_scrollspy_nav'),
    demo=lambda: demo.film(draw),
)

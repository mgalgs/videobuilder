"""Scroll-linked background shift: a page scrolls through its sections and
the background behind them blends from one section's colour to the next as
each boundary crosses the middle of the view."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def scroll_tint(scroll, sections, view_h, band=0.6):
    """The page background at scroll offset `scroll` (px from the top of the
    page), as an (r, g, b) tuple. `sections` is a list of `(height, colour)`
    stacked top to bottom; `view_h` is the viewport height. Each boundary
    blends over a band `band * view_h` tall centred on the viewport's middle,
    with a smoothstep, so the colour changes only while the boundary is in view
    and holds flat in between."""
    mid = scroll + view_h / 2
    half = max(1e-6, band * view_h / 2)
    color = sections[0][1]
    top = 0.0
    for (h, _), (_, nxt) in zip(sections, sections[1:]):
        top += h
        t = vb.clamp01((mid - (top - half)) / (2 * half))
        color = kit.mix(color, nxt, t * t * (3 - 2 * t))
    return color


def ink_on(color, light=demo.INK, dark='#16171c'):
    """A text colour readable on background `color`: `light` on dark grounds,
    `dark` on light ones, blended through the middle so it shifts with the
    background instead of snapping."""
    r, g, b, _ = vb.rgba(color)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return kit.mix(light, dark, vb.clamp01((lum - 0.3) / 0.15))


SECTIONS = [(470, demo.BG), (470, '#6f86f2'), (470, '#e6e8ef')]
COL_X, COL_W = demo.W / 2 - 300, 600


def _section(cv, top, label, ink):
    """One page section's content, its top edge at `top` on screen."""
    cv.line(COL_X, top + 30, COL_X + COL_W, top + 30, ink, width=2, alpha=0.25)
    demo.dot(cv, COL_X + 10, top + 104, r=8, color=ink)
    vb.text.draw(cv, [label], demo.font(22, 800), COL_X + 40, top + 70, ink, alpha=0.6)
    cv.rect(COL_X + 40, top + 108, 360, 26, ink, radius=6)
    cv.rect(COL_X + 40, top + 148, 220, 22, ink, radius=6, alpha=0.8)
    for i, w in enumerate((520, 480, 330)):
        cv.rect(COL_X + 40, top + 200 + i * 22, w, 8, ink, radius=4, alpha=0.45)
    cv.rect(COL_X + 40, top + 290, 520, 110, ink, radius=14, alpha=0.18)


def draw(n, cv):
    view_h = demo.H
    total = sum(h for h, _ in SECTIONS)
    end = total - view_h
    # two scrolls with a rest between, so the middle section's colour holds a beat
    stop = SECTIONS[0][0] + SECTIONS[1][0] / 2 - view_h / 2
    scroll = (stop * vb.ease_in_out_quart(demo.phase(n, 0.25, 1.25))
              + (end - stop) * vb.ease_in_out_quart(demo.phase(n, 1.65, 2.65)))
    bg = scroll_tint(scroll, SECTIONS, view_h)
    cv.fill(bg)
    ink = ink_on(bg)
    top = -scroll
    for i, (h, _) in enumerate(SECTIONS):
        if top < view_h and top + h > 0:
            _section(cv, top, f'SECTION {i + 1:02d}', ink)
        top += h
    # the scrollbar, so the motion reads as a page being scrolled
    tx, ty, th = demo.W - 34, 24, view_h - 48
    cv.rect(tx, ty, 6, th, ink, radius=3, alpha=0.15)
    thumb = th * view_h / total
    cv.rect(tx, ty + (th - thumb) * scroll / end, 6, thumb, ink, radius=3, alpha=0.7)
    cv.mark('page', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='scroll-linked-background-shift',
    name='Scroll-linked background shift',
    family='ui',
    group='Scroll',
    aliases=('section color morph', 'scroll tint', 'scroll-driven background color'),
    definition='As a page scrolls, the colour behind it eases from one section\'s hue into the next '
               'each time a new section moves into view.',
    phrasings=('the background colour changes as you scroll down through the sections',
               'each part of the page has its own colour and it blends over while scrolling',
               'scroll the page and let the backdrop morph from dark to blue to light'),
    related=('scroll-driven-text-reveal', 'theme-swap-crossfade', 'palette-shift-transition',
             'timeline-scroll', 'roll-up', 'gradient-shift-button'),
    api=('videobuilder.capabilities.ui.scroll_linked_background_shift.scroll_tint',
         'videobuilder.capabilities.ui.scroll_linked_background_shift.ink_on'),
    demo=lambda: demo.film(draw),
)

"""Infinite Scroll Append: a list scrolls toward its end, a loader shows
under the last row, and a fresh batch of rows fades up onto the bottom while
the list keeps scrolling into them."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def append_rows(base, added, p, stagger=0.15, rise=20, ease=vb.ease_out_quint):
    """Per-row `(index, alpha, dy)` for a list of `base` rows with `added`
    new rows arriving at progress `p` (0 -> 1). Old rows sit still; each new
    row fades in and rises `rise` px into place, `stagger` of the run after
    the one above it, the last landing at 1."""
    span = max(1e-6, 1 - stagger * max(0, added - 1))
    out = [(i, 1.0, 0.0) for i in range(base)]
    for k in range(added):
        q = ease(vb.clamp01((p - k * stagger) / span))
        out.append((base + k, q, rise * (1 - q)))
    return out


def draw_scroll_append(cv, x, y, w, h, row, base, added, scroll, p, row_h=56, gap=8, pad=10,
                       loader=0.0, spin=0.0, color=demo.ACCENT, track=demo.LINE, **kw):
    """A scrolling list in the viewport (x, y, w, h) with new rows appending
    at its foot. `row(cv, i, rx, ry, rw, rh)` draws row `i`; `scroll` is how
    far the content has moved up, in px; `p` (0 -> 1) runs the append (`kw`
    goes to `append_rows`). `loader` (0 -> 1) fades a spinner in just below
    the last loaded row, turned by `spin` (radians). A scrollbar on the right
    shrinks as the content grows. Returns the content height."""
    step = row_h + gap
    shown = base + (added if p > 0 else 0)
    content = pad * 2 + shown * step - gap
    with cv.clip(x, y, w, h, radius=12):
        for i, alpha, dy in append_rows(base, added if p > 0 else 0, p, **kw):
            ry = y + pad + i * step - scroll + dy
            if alpha <= 0 or ry > y + h or ry + row_h < y:
                continue
            with cv.layer(opacity=alpha):
                row(cv, i, x + pad, ry, w - pad * 3, row_h)
        if loader > 0:
            cy = y + pad + base * step - scroll + row_h / 2
            r = row_h * 0.2
            cv.arc(x + w / 2, cy, r, 0, 2 * math.pi, track, width=r * 0.28, alpha=loader)
            cv.arc(x + w / 2, cy, r, spin, spin + math.pi * 0.6, color, width=r * 0.28, alpha=loader)
            content = max(content, pad + base * step + row_h)
    view = h - 8
    thumb = max(24, view * min(1, h / content))
    t = vb.clamp01(scroll / max(1, content - h))
    cv.rect(x + w - pad * 1.2, y + 4 + (view - thumb) * t, 3, thumb, demo.MUTED, radius=1.5, alpha=0.8)
    return content


def _row(cv, i, x, y, w, h):
    cv.rect(x, y, w, h, '#1f2430', radius=h * 0.16)
    m = h * 0.2
    icon = h - 2 * m
    cv.rect(x + m, y + m, icon, icon, demo.ACCENT if i >= BASE else demo.TEAL, radius=icon * 0.25)
    bx, bar = x + 2 * m + icon, h * 0.11
    cv.rect(bx, y + h * 0.32, w * 0.42, bar, demo.INK, radius=bar / 2, alpha=0.9)
    cv.rect(bx, y + h * 0.32 + bar * 2, w * 0.26, bar, demo.MUTED, radius=bar / 2, alpha=0.8)


BASE, ADDED, ROW_H, GAP, PAD = 8, 4, 56, 8, 10


def draw(n, cv):
    w, h = 400, 470
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cv.shadow(x, y, w, h, radius=12, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, '#151922', radius=12)
    step = ROW_H + GAP
    end = PAD + BASE * step + ROW_H - h                 # first stop: the loader just in view
    more = PAD * 2 + (BASE + ADDED) * step - GAP - h  # then: the new batch's last row
    s1 = vb.ease_in_out_quart(demo.phase(n, 0.1, 1.0))
    s2 = vb.ease_in_out_quart(demo.phase(n, 1.75, 2.75))
    scroll = end * s1 + (more - end) * s2
    loading = demo.phase(n, 0.85, 1.0) * (1 - demo.phase(n, 1.35, 1.5))
    draw_scroll_append(cv, x, y, w, h, _row, BASE, ADDED, scroll, demo.phase(n, 1.4, 2.4),
                       row_h=ROW_H, gap=GAP, pad=PAD, loader=loading, spin=n / demo.FPS * 9)
    cv.mark('list', x, y, w, h)


TECHNIQUE = Technique(
    id='infinite-scroll-append',
    name='Infinite scroll append',
    family='ui',
    group='Layout & lists',
    aliases=('load more append', 'lazy list growth', 'endless scroll'),
    definition='As a list is scrolled near its last row, a brief loader appears and a new batch of rows '
               'fades up underneath, so the list simply keeps going.',
    phrasings=('the feed loads more items when you reach the bottom',
               'scroll down and new rows fade in at the end of the list',
               'an endless list that keeps adding cards as it scrolls'),
    related=('pull-to-refresh', 'infinite-marquee', 'fade-up-scroll-reveal', 'sticky-card-stack-on-scroll',
             'scrollspy-nav-indicator', 'scroll-driven-text-reveal'),
    api=('videobuilder.techniques.ui.infinite_scroll_append.draw_scroll_append',
         'videobuilder.techniques.ui.infinite_scroll_append.append_rows'),
    demo=lambda: demo.film(draw),
)

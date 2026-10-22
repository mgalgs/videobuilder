"""Fade-up scroll reveal: as a page scrolls, each block stays hidden until it
crosses a line low in the viewport, then fades in while rising a short way
into its place. It plays once on entry; it is not scrubbed by the scroll."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def fade_up(p, rise=30):
    """`(opacity, dy)` for a block at reveal progress `p` (0 -> 1): it fades
    in and rises from `rise` px below its place, decelerating to rest."""
    e = vb.ease_out_quint(vb.clamp01(p))
    return vb.clamp01(p * 1.6), rise * (1 - e)


def entry_time(top, scroll, view_h, threshold=0.85, until=60.0, step=1 / 120):
    """When a block whose top sits at page y `top` first crosses the trigger
    line at `threshold` of the viewport height `view_h`, given `scroll(t)`,
    the page's scroll offset in px at `t` seconds. 0 if it starts above the
    line; None if it never crosses before `until`."""
    t = 0.0
    while t <= until:
        if top - scroll(t) <= threshold * view_h:
            return t
        t += step
    return None


def reveal(t, top, scroll, view_h, length=0.6, delay=0.0, **kw):
    """Reveal progress (0 -> 1) at `t` for a block at page y `top`: it runs
    for `length` seconds from `delay` after the block enters (see
    `entry_time`, which `kw` goes to)."""
    t0 = entry_time(top, scroll, view_h, **kw)
    return 0.0 if t0 is None else vb.clamp01((t - t0 - delay) / length)


def fade_up_layer(cv, p, rise=30):
    """A `cv.layer` drawing its contents faded up at progress `p`:
    `with fade_up_layer(cv, p): draw_block(cv)`."""
    alpha, dy = fade_up(p, rise)
    return cv.layer(opacity=alpha, dy=dy)


# ---- demo: a page scrolling through a viewport, its rows fading up as they enter ----
VX, VY, VW, VH = 150, 35, 660, 470            # the viewport, in frame px
COL_W, ROW_H, GAP = 300, 125, 20
TOPS = [30 + i * (ROW_H + GAP) for i in range(7)]


SCROLL = 625


def scroll(t):
    return SCROLL * vb.ease_in_out_quart(vb.clamp01((t - 0.3) / 2.4))


def draw(n, cv):
    t = n / demo.FPS
    off = scroll(t)
    cv.rect(VX, VY, VW, VH, '#1d2026', radius=12)
    with cv.clip(VX, VY, VW, VH, radius=12):
        for row, top in enumerate(TOPS):
            for col in range(2):
                p = reveal(t, top, scroll, VH, delay=0.2 + 0.1 * col)
                x = VX + 20 + col * (COL_W + GAP)
                y = VY + top - off
                with fade_up_layer(cv, p, rise=40):
                    _block(cv, x, y, demo.ACCENT if (row + col) % 2 == 0 else demo.TEAL)
    # a scrollbar, so the page reads as scrolling
    track = VH - 20
    thumb = track * VH / (TOPS[-1] + ROW_H + 30)
    cv.rect(VX + VW - 10, VY + 10 + (track - thumb) * off / SCROLL, 4, thumb, demo.MUTED, radius=2, alpha=0.7)
    cv.mark('viewport', VX, VY, VW, VH)


def _block(cv, x, y, color):
    cv.shadow(x, y, COL_W, ROW_H, radius=10, dy=5, blur=14, color=(0, 0, 0, 0.45))
    cv.rect(x, y, COL_W, ROW_H, '#2a2e36', radius=10)
    cv.rect(x + 15, y + 15, 75, ROW_H - 30, color, radius=6)
    cv.rect(x + 105, y + 25, 150, 13, demo.INK, radius=6, alpha=0.95)
    cv.rect(x + 105, y + 50, 170, 9, demo.INK, radius=4, alpha=0.45)
    cv.rect(x + 105, y + 68, 130, 9, demo.INK, radius=4, alpha=0.45)


CAPABILITY = Capability(
    id='fade-up-scroll-reveal',
    name='Fade-up scroll reveal',
    family='ui',
    group='Scroll',
    aliases=('reveal on scroll', 'scroll fade-in', 'fade in up', 'animate on scroll'),
    definition='As a page scrolls, each section stays invisible until it nears the viewport, '
               'then fades in while drifting a short way up into place.',
    phrasings=('the cards fade in and slide up as you scroll down the page',
               'make each section appear softly from below when it scrolls into view',
               'content rises and fades in as the page scrolls'),
    related=('scroll-driven-text-reveal', 'roll-up', 'uncover', 'per-line-fade-in', 'tooltip-fade-follow',
             'zoom-out-reveal'),
    api=('videobuilder.capabilities.ui.fade_up_scroll_reveal.fade_up_layer',
         'videobuilder.capabilities.ui.fade_up_scroll_reveal.reveal',
         'videobuilder.capabilities.ui.fade_up_scroll_reveal.entry_time',
         'videobuilder.capabilities.ui.fade_up_scroll_reveal.fade_up'),
    demo=lambda: demo.film(draw),
)

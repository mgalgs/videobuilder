"""Shrinking Sticky Header: a tall page header that stays pinned to the top
while the content scrolls under it, collapsing to a slim bar as it goes."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def header_collapse(scroll, tall, short):
    """How far the header has collapsed (0 -> 1) after `scroll` px of
    scrolling: it gives up one px of height per px scrolled, from `tall` down
    to `short`, then stays put."""
    return vb.clamp01(scroll / max(tall - short, 1e-6))


def draw_sticky_header(cv, box, scroll, title, tall=150, short=60, color=demo.TEAL, ink=demo.BG,
                       big=52, small=26, subtitle=None, pad=28):
    """Draw a sticky header pinned to the top of `box` after `scroll` px of
    scrolling. Its height shrinks from `tall` to `short`; `title` shrinks from
    `big` to `small` and glides from the header's lower-left to its vertical
    centre; `subtitle` (optional) fades out as it collapses; a shadow under
    it grows in. Draw the scrolled content first, then this on top. Returns
    the header's current height."""
    c = header_collapse(scroll, tall, short)
    e = c * c * (3 - 2 * c)  # smoothstep: the title settles as the bar does
    x, y, w, _ = box
    h = tall + (short - tall) * c
    cv.shadow(x, y, w, h, dy=6, blur=22, color=(0, 0, 0, 0.5 * e))
    cv.rect(x, y, w, h, color)
    f = demo.font(big + (small - big) * e, 800)
    th = vb.text.block_size([title], f)[1]
    tall_y = y + h - pad - th - (34 if subtitle else 0)
    short_y = y + (h - th) / 2
    ty = tall_y + (short_y - tall_y) * e
    tb = vb.text.draw(cv, [title], f, x + pad, ty, ink)
    cv.mark('title', *tb)
    if subtitle and e < 1:
        vb.text.draw(cv, [subtitle], demo.font(20, 600), x + pad, ty + th + 6, ink, alpha=(1 - c) ** 2 * 0.75)
    return h


def _row(cv, x, y, w, h, i):
    cv.rect(x, y, w, h - 12, '#1d1f26', radius=14)
    demo.dot(cv, x + 40, y + (h - 12) / 2, r=20, color=(demo.ACCENT, demo.TEAL, demo.MUTED)[i % 3])
    cv.rect(x + 80, y + 18, w * (0.45 + 0.1 * (i % 3)), 12, demo.INK, radius=6, alpha=0.9)
    cv.rect(x + 80, y + 40, w * 0.3, 10, demo.MUTED, radius=5, alpha=0.7)


def draw(n, cv):
    pw, ph = 620, 470
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2
    tall, short, rowh = 170, 60, 82
    scroll = 380 * vb.ease_in_out_quart(demo.phase(n, 0.4, 2.6))
    cv.shadow(px, py, pw, ph, radius=22, dy=12, blur=36, color=(0, 0, 0, 0.5))
    with cv.clip(px, py, pw, ph, radius=22):
        cv.fill(demo.LINE)
        for i in range(12):
            ry = py + tall + 16 + i * rowh - scroll
            if py - rowh < ry < py + ph:
                _row(cv, px + 20, ry, pw - 40, rowh, i)
        draw_sticky_header(cv, (px, py, pw, ph), scroll, 'Inbox', tall, short, subtitle='12 new messages')
    cv.mark('panel', px, py, pw, ph)


TECHNIQUE = Technique(
    id='shrinking-sticky-header',
    name='Shrinking sticky header',
    family='ui',
    group='Scroll',
    aliases=('collapsing header', 'condensing header', 'shrink on scroll', 'compact sticky nav'),
    definition='A large header stays fixed at the top while the page scrolls beneath it, '
               'squeezing down into a thin bar with a smaller title as you scroll.',
    phrasings=('the big header gets smaller and sticks to the top when I scroll down',
               'as the list scrolls up the title bar collapses into a compact nav',
               'a tall app header that shrinks into a slim pinned bar on scroll'),
    related=('rubber-band-overscroll', 'station-id-bug', 'logo-build-on-reveal', 'accordion-height-expand',
             'row-collapse-removal', 'infinite-scroll-append'),
    api=('videobuilder.techniques.ui.shrinking_sticky_header.draw_sticky_header',
         'videobuilder.techniques.ui.shrinking_sticky_header.header_collapse'),
    demo=lambda: demo.film(draw),
)

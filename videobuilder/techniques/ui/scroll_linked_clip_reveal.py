"""Scroll-linked clip reveal: as a page scrolls, a photo's window grows from
a small rectangle to its full size, the picture itself staying put behind it,
so how much shows is tied to how far the section has come into view."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def scroll_progress(top, height, viewport, start=0.75, end=0.4):
    """How far a section has scrolled into view, 0 -> 1: 0 while its centre
    sits at `start` of the viewport height (1.0 would be the bottom edge), 1 once
    its centre has risen to `end`. `top` is the section's on-screen top."""
    centre = (top + height / 2) / viewport
    return vb.clamp01((start - centre) / (start - end))


def clip_window(box, p, small=(0.35, 0.45), radius=(12, 0)):
    """The visible window inside `box` at progress `p` (0 -> 1): `small` is
    its starting (width, height) as fractions of `box`, centred, opening to
    the whole box. Returns `(Box, corner radius)`, radius going from
    `radius[0]` to `radius[1]`."""
    box = vb.Box(*box)
    fw = small[0] + (1 - small[0]) * p
    fh = small[1] + (1 - small[1]) * p
    w, h = box.w * fw, box.h * fh
    window = vb.Box(box.x + (box.w - w) / 2, box.y + (box.h - h) / 2, w, h)
    return window, radius[0] + (radius[1] - radius[0]) * p


def draw_clip_reveal(cv, img, box, p, **kw):
    """Draw `img` covering `box`, seen only through the window `clip_window`
    gives at progress `p`: the image keeps its full-size framing while the
    window opens over it. Feed `p` from `scroll_progress` to link it to a
    scroll. `kw` goes to `clip_window`. Returns the window Box."""
    box = vb.Box(*box)
    window, r = clip_window(box, p, **kw)
    with cv.clip(*window, r):
        cv.image(img, *box.cover(img.w, img.h))
    cv.mark('image', *window)
    return window


# ---- demo: a page scrolling up past a photo section ----
U = demo.H / 540        # the demo's unit: sizes below are for a 540-high frame
SCROLL = 210 * U        # how far the page scrolls across the demo
IMG_TOP = 250 * U       # the photo section's top on the page, before scrolling
IMG_H = 300 * U
MARGIN = 36 * U


def _text_block(cv, x, y):
    cv.rect(x, y, 200 * U, 10 * U, demo.INK, radius=5 * U)
    cv.rect(x, y + 22 * U, 380 * U, 6 * U, demo.MUTED, radius=3 * U)
    cv.rect(x, y + 36 * U, 290 * U, 6 * U, demo.MUTED, radius=3 * U, alpha=0.7)


def draw(n, cv):
    s = SCROLL * vb.ease_in_out_quart(demo.phase(n, 0.3, 2.6))
    top = IMG_TOP - s
    box = vb.Box(MARGIN, top, demo.W - 2 * MARGIN - 20 * U, IMG_H)
    _text_block(cv, MARGIN + 10 * U, 50 * U - s)
    draw_clip_reveal(cv, demo.photo(), box, scroll_progress(top, IMG_H, demo.H))
    _text_block(cv, MARGIN + 10 * U, top + IMG_H + 30 * U)
    track_y, track_h, thumb = 20 * U, demo.H - 40 * U, (demo.H - 40 * U) * 0.35   # the scrollbar
    cv.rect(demo.W - 18 * U, track_y, 4 * U, track_h, demo.LINE, radius=2 * U)
    cv.rect(demo.W - 18 * U, track_y + (track_h - thumb) * s / SCROLL, 4 * U, thumb, demo.INK, radius=2 * U)


TECHNIQUE = Technique(
    id='scroll-linked-clip-reveal',
    name='Scroll-linked clip reveal',
    family='ui',
    group='Scroll',
    aliases=('scroll mask expand', 'growing window', 'scroll-driven clip-path reveal'),
    definition='As the page scrolls, a photo starts as a small cropped window that widens and '
               'heightens with the scroll until the whole picture is showing.',
    phrasings=('the image opens up from a little box to full width as you scroll down',
               'scrolling grows the picture\'s frame until it fills the section',
               'reveal the photo through a window that expands with the scroll'),
    related=('image-hover-mask-reveal', 'zoom-out-reveal', 'corner-wipe', 'scroll-driven-text-reveal',
             'circular-clip-reveal', 'text-mask-reveal'),
    api=('videobuilder.techniques.ui.scroll_linked_clip_reveal.draw_clip_reveal',
         'videobuilder.techniques.ui.scroll_linked_clip_reveal.clip_window',
         'videobuilder.techniques.ui.scroll_linked_clip_reveal.scroll_progress'),
    demo=lambda: demo.film(draw),
)

"""Carousel slide: a row of slides on a horizontal track glides sideways and
snaps the next slide into the centre, with the neighbours peeking in at the
edges and a row of dots marking which slide is showing."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def snap_position(s, hold=0.55, ease=vb.ease_in_out_quart):
    """A carousel's position for a running count `s` of slides (2.0 = two
    advances in): each whole step rests for its first `hold` fraction, then
    eases on to the next slide and snaps there. Pass `s = t / seconds_per_slide`
    for an auto-advancing carousel."""
    i = math.floor(s)
    return i + ease(vb.clamp01((s - i - hold) / (1 - hold)))


def draw_carousel(cv, slides, cx, cy, w, h, position, gap=40, view=None, dots=True,
                  dot_color=demo.INK, active_color=demo.ACCENT):
    """Draw `slides` (each `slide(cv, x, y, w, h)`) as a track of `w` x `h`
    cards `gap` apart, slid so fractional index `position` sits centred at
    (cx, cy). `view` (x, y, w, h) clips the track (default the whole frame);
    with `dots`, a pager under the track grows and lights the current dot.
    Returns the Box of the centred slide."""
    step = w + gap
    vx, vy, vw, vh = view or (0, 0, cv.width, cv.height)
    with cv.clip(vx, vy, vw, vh):
        for i, slide in enumerate(slides):
            x = cx - w / 2 + (i - position) * step
            if x + w < vx or x > vx + vw:
                continue
            slide(cv, x, cy - h / 2, w, h)
    if dots:
        r, pitch, dy = 6, 24, h / 2 + 34
        left = cx - pitch * (len(slides) - 1) / 2
        for i in range(len(slides)):
            near = vb.clamp01(1 - abs(i - position))
            dx = left + i * pitch
            demo.dot(cv, dx, cy + dy, r * (1 + 0.45 * near), color=dot_color, alpha=0.3 + 0.1 * near)
            if near > 0:
                demo.dot(cv, dx, cy + dy, r * (1 + 0.45 * near), color=active_color, alpha=near)
    return vb.Box(cx - w / 2, cy - h / 2, w, h)


TINTS = ('#1d6a8c', demo.ACCENT, demo.TEAL, '#7b5cc4')


def _slide(k):
    def draw(cv, x, y, w, h):
        img = demo.photo()
        cv.shadow(x, y, w, h, radius=18, dy=10, blur=26, color=(0, 0, 0, 0.5))
        with cv.clip(x, y, w, h, radius=18):
            cv.image(img, *vb.Box(x, y, w, h).cover(img.w, img.h))
            cv.rect(x, y, w, h, TINTS[k], alpha=0.45)
            demo.word(cv, f'{k + 1:02d}', x + 64, y + h - 46, size=52, weight=900)
    return draw


SLIDES = tuple(_slide(k) for k in range(len(TINTS)))


def draw(n, cv):
    w, h = 560, 330
    # Two advances: slide 1 -> 2 around 0.6 s, 2 -> 3 around 1.9 s, then rest.
    pos = snap_position(min(n / demo.FPS / 1.3, 2.0), hold=0.45)
    box = draw_carousel(cv, SLIDES, demo.W / 2, demo.H / 2 - 20, w, h, pos, gap=28, view=(0, 0, demo.W, demo.H))
    cv.mark('slide', *box)


TECHNIQUE = Technique(
    id='carousel-slide',
    name='Carousel slide',
    family='ui',
    group='Gestures & drag',
    aliases=('slider', 'horizontal slideshow', 'testimonial carousel', 'review slider', 'rotating testimonials'),
    definition='A strip of cards slides sideways and settles with the next card centred, its neighbours '
               'peeking in at the edges while a row of dots shows which one is up.',
    phrasings=('swipe through a few cards side to side like an app carousel',
               'slides that move left one at a time and snap into place, with page dots underneath',
               'a horizontal slider cycling through reviews'),
    related=('word-carousel-rotate', 'image-crossfade-slideshow', 'timeline-scroll', 'before-after-slider',
             'lower-third-slide-in-bar', 'layout-animation-flip'),
    api=('videobuilder.techniques.ui.carousel_slide.draw_carousel',
         'videobuilder.techniques.ui.carousel_slide.snap_position'),
    demo=lambda: demo.film(draw),
)

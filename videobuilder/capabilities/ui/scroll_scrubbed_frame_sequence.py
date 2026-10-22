"""Scroll-scrubbed frame sequence: a pinned viewer shows one still from a
numbered sequence, picked by how far the page is scrolled, so scrolling down
plays the clip forward and scrolling back up plays it in reverse."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def frame_index(scroll, count):
    """The frame of a `count`-frame sequence shown at `scroll` (0 = top of the
    scrubbed stretch, 1 = its end): 0 at the top, `count - 1` at the end, in
    equal steps between. `scroll` outside 0..1 holds the first or last frame."""
    return min(count - 1, int(vb.clamp01(scroll) * count))


def draw_scrubbed(cv, frames, scroll, x, y, w, h, count=None, radius=0):
    """Draw the frame of `frames` chosen by `scroll` into the box (x, y, w, h),
    clipped to `radius` corners. `frames` is a sequence of images (each drawn
    to cover the box) or a callable `frames(cv, i, box)` that draws frame `i`,
    with `count` saying how many there are. Returns the index drawn.

    In a film, drive `scroll` from the shot's own scroll offset, e.g.
    `draw_scrubbed(cv, stills, (offset - top) / distance, *viewer)`."""
    n = count if callable(frames) else len(frames)
    i = frame_index(scroll, n)
    box = vb.Box(x, y, w, h)
    with cv.clip(x, y, w, h, radius=radius):
        if callable(frames):
            frames(cv, i, box)
        else:
            img = frames[i]
            cv.image(img, *box.cover(img.w, img.h))
    return i


FRAMES = 12
SKY = ((0x2b, 0x2f, 0x5c), (0x6f, 0x8f, 0xc8))  # dusk -> day


def _mix(a, b, t):
    return '#%02x%02x%02x' % tuple(round(u + (v - u) * t) for u, v in zip(a, b))


def sunrise(cv, i, box, count=FRAMES):
    """Frame `i` of the demo's sequence: the sun climbs in an arc over two
    ranges of hills while the sky brightens."""
    t = i / (count - 1)
    cv.rect(box.x, box.y, box.w, box.h, _mix(*SKY, t))
    a = math.pi * (0.88 - 0.76 * t)
    sx = box.x + box.w * (0.5 + 0.4 * math.cos(a))
    sy = box.y + box.h * (0.62 - 0.45 * math.sin(a))
    demo.dot(cv, sx, sy, r=box.h * 0.09, color='#f4b942')
    for cx, cy, r, col in ((0.2, 1.25, 0.75, '#3e4a7a'), (0.85, 1.3, 0.8, '#3e4a7a'),
                           (0.5, 1.55, 0.85, '#252b4d'), (1.05, 1.6, 0.8, '#252b4d')):
        demo.dot(cv, box.x + box.w * cx, box.y + box.h * cy, r=box.h * r, color=col)


def scroll_at(n):
    """The demo's scroll: down to the end, a beat, then back up most of the way."""
    down = vb.ease_in_out_quart(demo.phase(n, 0.25, 1.55))
    up = vb.ease_in_out_quart(demo.phase(n, 1.9, 2.8))
    return down - 0.7 * up


def draw(n, cv):
    s = scroll_at(n)
    px, py, pw, ph = 230, 40, 500, 460          # the page
    cv.shadow(px, py, pw, ph, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(px, py, pw, ph, '#1c1e25', radius=18)
    cv.outline(px, py, pw, ph, demo.LINE, width=2, radius=18)

    # page copy scrolling past above the pinned viewer
    with cv.clip(px + 30, py + 20, pw - 80, 50):
        for k in range(6):
            ly = py + 34 + k * 22 - s * 110
            cv.rect(px + 34, ly, (300, 220, 340, 260, 310, 200)[k], 7, demo.MUTED, radius=3, alpha=0.6)

    vx, vy, vw, vh = px + 30, py + 84, pw - 80, 236  # the pinned viewer
    i = draw_scrubbed(cv, sunrise, s, vx, vy, vw, vh, count=FRAMES, radius=10)
    cv.mark('viewer', vx, vy, vw, vh)

    # the sequence as a filmstrip, the frame on screen outlined
    tw, gap = (vw - (FRAMES - 1) * 4) / FRAMES, 4
    for k in range(FRAMES):
        tx, ty = vx + k * (tw + gap), vy + vh + 22
        with cv.clip(tx, ty, tw, 26, radius=3):
            sunrise(cv, k, vb.Box(tx, ty, tw, 26))
        if k != i:
            cv.rect(tx, ty, tw, 26, '#000000', radius=3, alpha=0.35)
    cv.outline(vx + i * (tw + gap) - 2, vy + vh + 20, tw + 4, 30, demo.ACCENT, width=3, radius=4)
    f = demo.mono(20, 700)
    vb.text.draw(cv, [f'frame {i + 1:02d} / {FRAMES}'], f, vx, vy + vh + 66, demo.INK)

    # the scrollbar: its thumb is the scroll position
    bx, by, bh = px + pw - 26, py + 24, ph - 48
    cv.rect(bx, by, 8, bh, demo.LINE, radius=4)
    cv.rect(bx, by + s * (bh - 70), 8, 70, demo.INK, radius=4)
    going = scroll_at(n + 1) - s
    if abs(going) > 1e-3:
        arrow = 'scroll ↓' if going > 0 else 'scroll ↑'
        vb.text.draw(cv, [arrow], demo.font(22, 700), px + pw + 20, by + s * (bh - 70) + 20, demo.TEAL)


TECHNIQUE = Technique(
    id='scroll-scrubbed-frame-sequence',
    name='Scroll-scrubbed frame sequence',
    family='ui',
    group='Scroll',
    aliases=('image sequence scrub', 'frame scroll', 'scroll-driven image sequence'),
    definition='A pinned picture steps through a numbered run of stills in time with the page scroll, '
               'so scrolling down plays the clip forward and scrolling up plays it backward.',
    phrasings=('as you scroll, the animation plays, and scrolling back rewinds it',
               'tie the image sequence to the scrollbar so the reader drives the frames',
               'a product shot that turns frame by frame while the page scrolls'),
    related=('scroll-driven-text-reveal', 'roll-up', 'timeline-scroll', 'frame-by-frame-hand-drawn-animation',
             'seamless-loop', 'interruptible-motion'),
    api=('videobuilder.techniques.ui.scroll_scrubbed_frame_sequence.draw_scrubbed',
         'videobuilder.techniques.ui.scroll_scrubbed_frame_sequence.frame_index'),
    demo=lambda: demo.film(draw),
)

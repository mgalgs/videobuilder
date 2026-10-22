"""Image Hover Mask Reveal: a pointer rests on an image and a circle opens
out from under it, showing a second image through the hole until it fills
the frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def reach(x, y, w, h, px, py):
    """The radius a circle centred on (px, py) needs to cover the box (x, y, w, h):
    the distance to its farthest corner."""
    return max(math.hypot(cx - px, cy - py) for cx in (x, x + w) for cy in (y, y + h))


def hover_mask_reveal(cv, base, reveal, x, y, w, h, px, py, p, radius=0, edge=None, edge_width=2):
    """Draw `base(cv)` in the box (x, y, w, h), then `reveal(cv)` through a
    circle centred on the pointer (px, py) whose radius runs 0 -> enough to
    cover the box as `p` runs 0 -> 1 (ease `p` yourself). Both are clipped to
    the box, rounded by `radius`. `edge`, a colour, rings the mask's rim.

    Move (px, py) frame by frame and the hole follows the pointer; run `p`
    back down on mouse-out and it closes again."""
    c = cv.ctx
    with cv.clip(x, y, w, h, radius):
        base(cv)
        r = vb.clamp01(p) * reach(x, y, w, h, px, py)
        if r <= 0:
            return
        c.save()
        c.new_path()
        c.arc(px, py, r, 0, 2 * math.pi)
        c.clip()
        reveal(cv)
        c.restore()
        if edge and p < 1:
            cv.arc(px, py, r, 0, 2 * math.pi, edge, width=edge_width, alpha=0.8 * (1 - vb.clamp01(p)))


def pointer(cv, x, y, size=34, color='#ffffff', outline='#111111'):
    """A mouse-arrow cursor with its tip at (x, y)."""
    s = size / 34
    pts = [(0, 0), (0, 27), (7, 21), (12, 32), (17, 30), (12, 19.5), (21, 19.5)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    c = cv.ctx
    cv.shape_shadow(pts, dx=2 * s, dy=3 * s, blur=6 * s, color=(0, 0, 0, 0.45))
    c.save()
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_line_width(2 * s)
    c.set_line_join(1)  # round
    c.set_source_rgba(*vb.rgba(outline))
    c.stroke()
    c.restore()


CARD_W, CARD_H = 560, 340
CARD_X, CARD_Y = (demo.W - CARD_W) / 2, (demo.H - CARD_H) / 2 - 10


def _photo(cv):
    img = demo.photo()
    cv.image(img, *vb.Box(CARD_X, CARD_Y, CARD_W, CARD_H).cover(img.w, img.h))


def _dusk(cv):
    _photo(cv)
    cv.rect(CARD_X, CARD_Y, CARD_W, CARD_H, '#1c2340', alpha=0.72)


def draw(n, cv):
    # The pointer glides in from the lower right and settles on the image, the
    # circle opens from it and the pointer drifts a little while it does.
    rest = (CARD_X + CARD_W * 0.42, CARD_Y + CARD_H * 0.45)
    start = (demo.W - 150, demo.H - 50)
    m = vb.ease_out_quint(demo.phase(n, 0.15, 0.95))
    drift = vb.ease_in_out_quart(demo.phase(n, 1.0, 2.4))
    px = start[0] + (rest[0] - start[0]) * m + 40 * drift
    py = start[1] + (rest[1] - start[1]) * m - 14 * drift
    p = vb.ease_in_out_quart(demo.phase(n, 1.0, 2.4))
    cv.shadow(CARD_X, CARD_Y, CARD_W, CARD_H, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.5))
    hover_mask_reveal(cv, _dusk, _photo, CARD_X, CARD_Y, CARD_W, CARD_H, px, py, p, radius=18,
                      edge='#ffffff')
    cv.mark('image', CARD_X, CARD_Y, CARD_W, CARD_H)
    pointer(cv, px, py, size=28)


CAPABILITY = Capability(
    id='image-hover-mask-reveal',
    name='Image hover mask reveal',
    family='ui',
    group='Cursor & hover',
    aliases=('mask reveal on hover', 'curtain hover', 'hover circle reveal'),
    definition='When the pointer rests on an image, a circle swells out from the cursor and uncovers '
               'a second version of the picture underneath until it fills the frame.',
    phrasings=('hovering over the photo opens a circle from the mouse that shows a different image',
               'the cursor punches a growing hole in the picture to reveal what is behind it',
               'mouse over the image and the alternate version spreads out from the pointer'),
    related=('scroll-linked-clip-reveal', 'text-mask-reveal', 'logo-mask-wipe-reveal', 'hover-reveal-actions',
             'shutter-slat-reveal', 'brush-stroke-paint-reveal'),
    api=('videobuilder.capabilities.ui.image_hover_mask_reveal.hover_mask_reveal',
         'videobuilder.capabilities.ui.image_hover_mask_reveal.pointer',
         'videobuilder.capabilities.ui.image_hover_mask_reveal.reach'),
    demo=lambda: demo.film(draw),
)

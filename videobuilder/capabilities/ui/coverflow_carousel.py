"""Coverflow Carousel: a row of covers where the one in front faces the
viewer flat and full size, and the rest stand angled back on either side
like records in a crate; scrolling swings each cover round as it passes the
middle."""
import math

import cairo
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def coverflow_layout(d, gap=0.78, spacing=0.3, depth=0.8, angle=65):
    """Where a cover `d` places from the front one sits: `(x, z, theta)`, `x`
    and `z` in cover widths (`z` away from the viewer), `theta` its turn
    about the vertical in degrees. Between -1 and 1 it swings and slides
    smoothly; further out each cover is only `spacing` widths along."""
    near = max(-1.0, min(1.0, d))
    x = gap * near + spacing * (d - near)
    return x, depth * abs(near), -angle * near


def draw_cover(cv, img, cx, cy, w, h, x, z, theta, focal=1.8, strips=48, alpha=1.0, reflect=0.0):
    """Draw `img` as a `w` x `h` cover at (`x`, `z`) cover widths from the
    front slot centred on (`cx`, `cy`), turned `theta` degrees about the
    vertical, in perspective with focal length `focal` cover widths. Drawn as
    `strips` vertical slices, each scaled for its depth. `reflect` > 0 adds a
    mirrored copy below at that opacity. Returns the Box it covers."""
    f = focal * w
    t = math.radians(theta)
    c = cv.ctx
    surf, mip = img.for_scale(w / img.w * cv.scale_factor())

    def project(u):  # u: -0.5 .. 0.5 across the cover
        wx, wz = (x + u * math.cos(t)) * w, (z + u * math.sin(t)) * w
        k = f / (f + wz)
        return cx + wx * k, k

    xs, ks = zip(*(project(-0.5 + i / strips) for i in range(strips + 1)))

    def slices(flip):
        for i in range(strips):
            x0, x1 = xs[i], xs[i + 1]
            if x1 - x0 < 0.05:
                continue
            k = (ks[i] + ks[i + 1]) / 2
            ix0, ix1 = img.w * i / strips, img.w * (i + 1) / strips
            sx = (x1 - x0) / (ix1 - ix0)
            c.save()
            # the mirror image hangs from the cover's bottom edge, a small gap below it
            c.translate(x0, cy - h * k / 2 if flip > 0 else cy + 1.5 * h * k + 4 * k)
            c.scale(sx * mip, flip * h * k / img.h * mip)
            # a hair of overlap so neighbouring slices leave no seam
            c.rectangle((-0.6 / sx) / mip, 0, (ix1 - ix0 + 1.2 / sx) / mip, img.h / mip)
            c.clip()
            c.set_source_surface(surf, -ix0 / mip, 0)
            c.get_source().set_filter(cairo.FILTER_GOOD)
            c.paint()
            c.restore()

    # each pass is one group, so the overlapping slices composite once at the pass's opacity
    for flip, a in ((-1, alpha * reflect), (1, alpha)):
        if a > 0:
            c.push_group()
            slices(flip)
            c.pop_group_to_source()
            c.paint_with_alpha(a)
    left, right = min(xs), max(xs)
    hk = h * max(ks)
    return vb.Box(left, cy - hk / 2, right - left, hk)


def draw_coverflow(cv, covers, pos, cx, cy, w, h, reflect=0.25, floor=None, **layout):
    """Draw the carousel with `covers` (a list of `vb.Image`) scrolled to
    `pos`: cover `i` sits `i - pos` places from the front, so a fractional
    `pos` is mid-swipe. Far covers draw first. `reflect` is the mirrored
    copies' opacity; `floor` (a colour) fades them out into it. `layout`
    goes to `coverflow_layout`. Returns the front cover's Box."""
    order = sorted(range(len(covers)), key=lambda i: -abs(i - pos))
    front = None
    for i in order:
        x, z, theta = coverflow_layout(i - pos, **layout)
        box = draw_cover(cv, covers[i], cx, cy, w, h, x, z, theta, reflect=reflect)
        if front is None or abs(i - pos) < front[0]:
            front = abs(i - pos), box
    if floor is not None and reflect > 0:
        top = cy + h / 2
        g = cairo.LinearGradient(0, top, 0, top + h * 0.6)
        r, gr, b, _ = vb.rgba(floor)
        g.add_color_stop_rgba(0, r, gr, b, 0.35)
        g.add_color_stop_rgba(1, r, gr, b, 1.0)
        cv.ctx.rectangle(0, top, cv.width, cv.height - top)
        cv.ctx.set_source(g)
        cv.ctx.fill()
    return front[1] if front else None


COLORS = ('#ef5b4c', '#4fc3b0', '#f2b84b', '#7b8cff', '#e86fb0', '#5fbf6a', '#f08a3c')
SIZE = 220


def _cover(i):
    """A square demo cover: a coloured panel with a big numeral."""
    cv = vb.Canvas(SIZE, SIZE, background=COLORS[i % len(COLORS)])
    cv.rect(0, SIZE * 0.62, SIZE, SIZE * 0.38, '#000000', alpha=0.18)
    demo.word(cv, str(i + 1), SIZE / 2, SIZE * 0.42, size=110, color=demo.INK, weight=900)
    cv.surface.flush()
    return vb.Image.from_pil(PILImage.frombuffer('RGBA', (SIZE, SIZE), cv.bgra(), 'raw', 'BGRA', 0, 1))


_COVERS = []


def draw(n, cv):
    if not _COVERS:
        _COVERS.extend(_cover(i) for i in range(7))
    p1, p2 = demo.phase(n, 0.35, 1.25), demo.phase(n, 1.6, 2.6)
    pos = 1 + 2 * (1 - (1 - p1) ** 3) + 2 * (1 - (1 - p2) ** 3)  # two swipes, each easing to rest
    box = draw_coverflow(cv, _COVERS, pos, demo.W / 2, demo.H * 0.44, SIZE, SIZE, floor=demo.BG)
    cv.mark('cover', *box)


TECHNIQUE = Technique(
    id='coverflow-carousel',
    name='Coverflow carousel',
    family='ui',
    group='Gestures & drag',
    aliases=('cover flow', '3D carousel', 'album carousel', 'perspective carousel'),
    definition='A row of covers scrolls sideways with the middle one facing you flat while the others '
               'stand tilted back on each side, each cover swinging round as it passes through the centre.',
    phrasings=('flip through album covers like browsing records, the middle one facing front',
               'a 3D carousel where the side cards angle away and the centre one is flat',
               'swipe across a row of tilted thumbnails that turn to face you in the middle'),
    related=('slide-over-cover', 'swirl', 'roll-up', 'image-crossfade-slideshow', 'pan', 'word-carousel-rotate'),
    api=('videobuilder.techniques.ui.coverflow_carousel.draw_coverflow',
         'videobuilder.techniques.ui.coverflow_carousel.coverflow_layout',
         'videobuilder.techniques.ui.coverflow_carousel.draw_cover'),
    demo=lambda: demo.film(draw),
)

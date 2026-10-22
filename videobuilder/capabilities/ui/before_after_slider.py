"""Before-after slider: two versions of one picture stacked in the same
frame, with a vertical divider and a round handle that slides sideways; left
of the divider shows the before, right of it the after."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def before_after_slider(cv, before, after, split, box=None, line='#f4f4f2', ring=demo.ACCENT, handle_r=22,
                        labels=('BEFORE', 'AFTER')):
    """Draw the comparison with the divider at `split` (0 -> 1 across `box`,
    default the whole frame): `before(cv)` shows left of it, `after(cv)`
    right of it, each drawn full-size and clipped, so the picture never
    moves -- only the line does. `labels` (or None) sit in each side's top
    corner and are covered along with their side. Returns the handle's
    centre.

    In a film, drive `split` from a curve over the shot, e.g.
    `before_after_slider(cv, old, new, slider_sweep(shot.f / shot.length))`."""
    x, y, w, h = box or (0, 0, cv.width, cv.height)
    sx = x + w * vb.clamp01(split)
    with cv.clip(x, y, w, h):
        before(cv)
        if sx < x + w:
            with cv.clip(sx, y, x + w - sx, h):
                after(cv)
        if labels:
            f = demo.mono(15, 700)
            for text, side in zip(labels, ('left', 'right')):
                tw, th = vb.text.block_size([text], f)
                cw, ch = tw + 28, th + 14
                cx = x + 24 if side == 'left' else x + w - 24 - cw
                region = (x, y, sx - x, h) if side == 'left' else (sx, y, x + w - sx, h)
                if region[2] <= 0:
                    continue
                with cv.clip(*region):
                    cv.rect(cx, y + 24, cw, ch, demo.BG, radius=ch / 2, alpha=0.8)
                    vb.text.draw(cv, [text], f, cx + 14, y + 31, line)
        # the divider, a soft glow either side, and the grab handle
        cv.rect(sx - 8, y, 16, h, line, alpha=0.12)
        cv.rect(sx - 1.5, y, 3, h, line)
    hx, hy = sx, y + h / 2
    cv.shadow(hx - handle_r, hy - handle_r, 2 * handle_r, 2 * handle_r, radius=handle_r, dy=4, blur=12,
              color=(0, 0, 0, 0.45))
    cv.sector(hx, hy, handle_r, 0, 2 * math.pi, line)
    ctx = cv.ctx
    ctx.arc(hx, hy, handle_r, 0, 2 * math.pi)
    ctx.set_source_rgba(*vb.rgba(ring))
    ctx.set_line_width(3)
    ctx.stroke()
    a = handle_r * 0.22
    for s in (-1, 1):
        ctx.move_to(hx + s * a, hy - a * 1.3)
        ctx.line_to(hx + s * a * 2.6, hy)
        ctx.line_to(hx + s * a, hy + a * 1.3)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(demo.BG))
        ctx.fill()
    cv.mark('handle', hx - handle_r, hy - handle_r, 2 * handle_r, 2 * handle_r)
    return hx, hy


def slider_sweep(p, rest=0.5, far=(0.85, 0.15)):
    """A divider position for progress `p` (0 -> 1): eases from `rest` out
    to `far[0]`, across to `far[1]`, and back to `rest` -- the way someone
    drags a comparison handle to look at each side, then lets it settle."""
    stops = (rest, *far, rest)
    seg = min(len(stops) - 2, int(vb.clamp01(p) * (len(stops) - 1)))
    t = vb.clamp01(p) * (len(stops) - 1) - seg
    return stops[seg] + (stops[seg + 1] - stops[seg]) * vb.ease_in_out_quart(t)


def _photo(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def _before(cv):
    """The photo drained of colour and dimmed: the 'unedited' side."""
    _photo(cv)
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_HSL_SATURATION)
    ctx.set_source_rgb(0.5, 0.5, 0.5)
    ctx.paint()
    ctx.restore()
    cv.fill('#000000', alpha=0.25)


def draw(n, cv):
    before_after_slider(cv, _before, _photo, slider_sweep(demo.phase(n, 0.3, 2.8)))


TECHNIQUE = Technique(
    id='before-after-slider',
    name='Before-after slider',
    family='ui',
    group='Cards & media',
    aliases=('image comparison slider', 'before/after wipe', 'compare slider'),
    definition='Two versions of the same picture share one frame, and a draggable vertical line with a handle '
               'slides across it, showing the old version on one side and the new one on the other.',
    phrasings=('a slider you drag over the photo to compare before and after',
               'show the original and the edited image split by a line that moves back and forth',
               'reveal the change by sweeping a divider across the picture'),
    related=('range-slider-value-bubble', 'carousel-slide', 'scroll-scrubbed-frame-sequence', 'cross-dissolve',
             'pixelate-transition', 'difference-highlight'),
    api=('videobuilder.techniques.ui.before_after_slider.before_after_slider',
         'videobuilder.techniques.ui.before_after_slider.slider_sweep',
         'videobuilder.compendium.components.images_before_after.COMPONENT'),
    demo=lambda: demo.film(draw),
)

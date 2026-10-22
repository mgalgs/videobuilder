"""Pixel Sort Text: horizontal bands of the lettering have their pixels
sorted by brightness, so the letters smear into hard streaks, then the sort
lets go and the word comes back clean."""
import random
from contextlib import contextmanager

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _brightness(px):
    # cairo ARGB32 in memory is premultiplied B, G, R, A.
    return px[2] * 299 + px[1] * 587 + px[0] * 114


def _sort_span(data, row, x0, x1, toward_left):
    """Sort the pixels [x0, x1) of the row starting at byte `row`, brightest
    first (or last), in place."""
    a, b = row + x0 * 4, row + x1 * 4
    pixels = [data[i:i + 4] for i in range(a, b, 4)]
    pixels.sort(key=_brightness, reverse=toward_left)
    data[a:b] = b''.join(pixels)


@contextmanager
def pixel_sorted(cv, x, y, w, h, amount, seed=0, reach=None, band=(2, 10), still=0.2, toward='left'):
    """A group over the region (x, y, w, h) whose pixels are sorted along
    rows by brightness when it is painted back. The body draws with the
    *yielded* Canvas, in the region's own coordinates (0, 0 is its top-left).

    Rows go in bands `band` px tall (a random height in that range); each
    band sorts one span of its row, up to `amount` (0 -> 1) times `reach` px
    long (default `w`), its length scaled by a per-band weight, so bright
    pixels pile up at the span's `toward` end ('left' or 'right') as a
    streak. A `still` fraction of bands never sorts. At `amount` 0 the
    region paints exactly as drawn. The bands come from `seed`, so animating
    `amount` alone grows and shrinks the same streaks frame to frame."""
    sf = cv.scale_factor()
    sub = vb.Canvas(w, h, scale=sf, format=cv.format)
    yield sub
    surf = sub.surface
    surf.flush()
    if amount > 0:
        dw, dh, stride = surf.get_width(), surf.get_height(), surf.get_stride()
        data = surf.get_data()
        buf = bytearray(data)
        reach_px = (w if reach is None else reach) * sf
        left = toward == 'left'
        rng = random.Random(seed)
        row = 0
        while row < dh:
            tall = max(1, round(rng.uniform(*band) * sf))
            weight = 0.0 if rng.random() < still else 0.25 + 0.75 * rng.random()
            anchor = 0.5 + 0.5 * rng.random()  # spans end in the far half, so they cross the content
            span = round(min(1.0, amount) * weight * reach_px)
            if span > 1:
                if left:
                    x1 = round(anchor * dw)
                    x0 = max(0, x1 - span)
                    x1 = min(dw, max(x1, x0 + span))
                else:
                    x0 = round((1 - anchor) * dw)
                    x1 = min(dw, x0 + span)
                    x0 = max(0, min(x0, x1 - span))
                for r in range(row, min(dh, row + tall)):
                    _sort_span(buf, r * stride, x0, x1, left)
            row += tall
        data[:] = buf
        surf.mark_dirty()
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(1 / sf, 1 / sf)
    c.set_source_surface(surf, 0, 0)
    c.get_source().set_filter(cairo.FILTER_NEAREST)
    c.paint()
    c.restore()


def draw_pixel_sort_text(cv, text, font, x, y, amount, color, seed=0, reach=None, **kw):
    """Draw one line of `text` from its top-left (x, y), pixel-sorted by
    `amount` (0: clean letters, 1: full streaks). Streaks run up to `reach`
    px (default 0.4 of the line's width) past the line toward `toward`
    (default 'left'); `kw` goes to `pixel_sorted`. Returns the line's Box."""
    w, h = vb.text.block_size([text], font)
    reach = w * 0.4 if reach is None else reach
    toward = kw.get('toward', 'left')
    pad_l, pad_r = (reach, 4) if toward == 'left' else (4, reach)
    with pixel_sorted(cv, x - pad_l, y, w + pad_l + pad_r, h, amount, seed=seed,
                      reach=w + reach, **kw) as sub:
        vb.text.draw(sub, [text], font, pad_l, 0, color)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(100, 900)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    # Clean, smear out into streaks, hold, then sort back into the letters.
    amount = vb.ease_out_quint(demo.phase(n, 0.3, 0.9)) * (1 - vb.ease_in_out_quart(demo.phase(n, 1.3, 2.4)))
    box = draw_pixel_sort_text(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, amount, demo.INK, seed=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='pixel-sort-text',
    name='Pixel sort text',
    family='typography',
    group='Glitch and distortion',
    aliases=('pixel streak text', 'glitch pixel sort reveal'),
    definition='Strips of a word have their pixels reordered from bright to dark, dragging the letters '
               'into hard horizontal streaks that then pull back into clean type.',
    phrasings=('the title smears sideways into glitchy streaks and then snaps back',
               'a datamosh-style pixel sort on the headline',
               'letters melt into horizontal light streaks before settling'),
    related=('pixel-sorting', 'pixelation-reveal', 'dot-matrix-text', 'letter-sort-animation',
             'ascii-art-render', 'pixel-build'),
    api=('videobuilder.capabilities.typography.pixel_sort_text.draw_pixel_sort_text',
         'videobuilder.capabilities.typography.pixel_sort_text.pixel_sorted'),
    demo=lambda: demo.film(draw),
)

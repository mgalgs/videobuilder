"""Brush Stroke Paint Reveal: a wide brush sweeps back and forth across a
region in a few overlapping passes, and wherever it has painted the content
underneath shows through, its edges ragged with bristle marks."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

_STROKE = vb.bezier(0.4, 0.0, 0.6, 1.0)  # each pass starts and ends a little slower, like a hand


def _bristles(rows, per_row, overlap, seed):
    """Per row, a list of `(top, height, lag)` in row-relative units:
    `top`/`height` as fractions of the row, `lag` as a fraction of `jag`."""
    rng = random.Random(f'brush:{seed}')
    out = []
    for _ in range(rows):
        row = []
        span = 1 + 2 * overlap
        for k in range(per_row):
            top = -overlap + span * k / per_row + rng.uniform(-0.3, 0.3) * span / per_row
            row.append((top, span / per_row * rng.uniform(1.1, 2.2), rng.random() ** 1.5))
        out.append(row)
    return out


def brush_reveal(cv, content, x, y, w, h, p, rows=3, bristles=48, jag=45, overlap=0.18, seed=0,
                 streaks=0.12):
    """Draw `content(cv)` showing only where a brush has painted by progress
    `p` (0 -> 1) over the box (x, y, w, h). The brush makes `rows` passes,
    top to bottom, alternating left-to-right and right-to-left, each pass a
    band of `bristles` thin hairs whose ends trail raggedly by up to `jag`
    px; neighbouring passes overlap by `overlap` of a row so no seam shows.
    `streaks` is the strength of the faint dry-brush lines left over the
    painted area (0 for none). The same `seed` gives the same brush."""
    p = vb.clamp01(p)
    if p <= 0:
        return
    c = cv.ctx
    band = h / rows
    hairs = _bristles(rows, bristles, overlap, seed)
    reach = w + jag  # the head travels past the far edge so the ragged end clears it
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    c.new_path()
    for r, row in enumerate(hairs):
        q = vb.clamp01(p * rows - r)
        if q <= 0:
            break
        head = _STROKE(q) * reach
        for top, height, lag in row:
            end = head - lag * jag
            if end <= 0:
                continue
            ty = y + band * (r + top)
            if r % 2 == 0:
                c.rectangle(x, ty, end, band * height)
            else:
                c.rectangle(x + w - end, ty, end, band * height)
    c.clip()
    content(cv)
    if streaks > 0:
        rng = random.Random(f'streaks:{seed}')
        for _ in range(int(h / 8)):
            sy = y + rng.uniform(0, h)
            shade = '#000000' if rng.random() < 0.6 else '#ffffff'
            cv.rect(x, sy, w, rng.uniform(0.8, 2.4), shade, alpha=streaks * rng.uniform(0.3, 1.0))
    c.restore()


def _scene(cv, x, y, w, h):
    img = demo.photo()
    with cv.clip(x, y, w, h):
        cv.image(img, *vb.Box(x, y, w, h).cover(img.w, img.h))


def draw(n, cv):
    w, h = 640, 360
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    brush_reveal(cv, lambda c: _scene(c, x, y, w, h), x, y, w, h, demo.phase(n, 0.3, 2.5), seed=3)
    cv.mark('painted', x, y, w, h)


TECHNIQUE = Technique(
    id='brush-stroke-paint-reveal',
    name='Brush stroke paint reveal',
    family='shapes',
    group='Liquid & organic',
    aliases=('paint wipe', 'brush-on reveal', 'paint stroke wipe', 'brush stroke reveal', 'brush mask reveal'),
    definition='A broad brush drags across the area in a few back-and-forth passes, and the picture '
               'appears only where its rough, bristly stroke has been laid down.',
    phrasings=('paint the image onto the screen with big brush strokes',
               'reveal the picture as if someone is brushing it on',
               'the content shows up underneath a sweeping paint stroke'),
    related=('paint-brush-wipe', 'handwriting-reveal', 'text-mask-reveal', 'logo-mask-wipe-reveal',
             'image-hover-mask-reveal', 'uncover'),
    api=('videobuilder.techniques.shapes.brush_stroke_paint_reveal.brush_reveal',),
    demo=lambda: demo.film(draw),
)

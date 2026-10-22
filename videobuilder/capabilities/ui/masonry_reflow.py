"""Masonry reflow: cards of mixed heights packed into columns glide to their
new packed places when some are filtered out (or the column count changes),
each column closing up its gaps instead of the grid jumping."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def masonry_layout(heights, columns, x, y, width, gap=24):
    """Pack items of the given `heights` into `columns` equal columns
    spanning `width` from (x, y): each item goes, in order, to the top of
    whichever column is currently shortest. Returns one `vb.Box` per item."""
    col_w = (width - gap * (columns - 1)) / columns
    tops = [y] * columns
    out = []
    for h in heights:
        c = min(range(columns), key=lambda i: (tops[i], i))
        out.append(vb.Box(x + c * (col_w + gap), tops[c], col_w, h))
        tops[c] += h + gap
    return out


def reflow(before, after, p, stagger=0.4, ease=vb.ease_in_out_quart):
    """Every item's box at progress `p` (0 -> 1) of a reflow from `before` to
    `after` (equal-length lists of `vb.Box`, or None where the item is not in
    that layout), as `(box, alpha, scale)` triples, or None for an item in
    neither. Items are staggered in list order across `stagger` of the run;
    an item only in `before` fades and shrinks out over the first third, one
    only in `after` grows in over the last third."""
    n = len(before)
    out = []
    for i, (a, b) in enumerate(zip(before, after)):
        if a is None and b is None:
            out.append(None)
            continue
        if b is None:
            q = vb.clamp01(p * 3)
            out.append((a, 1 - q, 1 - 0.25 * q))
            continue
        if a is None:
            q = ease(vb.clamp01(p * 3 - 2))
            out.append((b, q, 0.75 + 0.25 * q))
            continue
        start = stagger * i / max(n - 1, 1)
        q = ease(vb.clamp01((p - start) / (1 - stagger)))
        out.append((vb.Box(a.x + (b.x - a.x) * q, a.y + (b.y - a.y) * q,
                           a.w + (b.w - a.w) * q, a.h + (b.h - a.h) * q), 1.0, 1.0))
    return out


HEIGHTS = (92, 132, 76, 112, 150, 86, 122, 82, 140, 102, 96, 116)
KEEP = (True, False, True, True, False, True, False, True, True, False, True, False)
GRID_X, GRID_Y, GRID_W, COLS, GAP = 220, 104, 520, 4, 14


def _chip(cv, x, y, w, active, dots):
    cv.rect(x, y, w, 30, demo.LINE, radius=15)
    if active:
        cv.rect(x, y, w, 30, demo.ACCENT, radius=15, alpha=0.18)
        cv.outline(x, y, w, 30, demo.ACCENT, width=2, radius=15)
    for i, c in enumerate(dots):
        demo.dot(cv, x + 17 + i * 15, y + 15, 5, color=c)


def draw(n, cv):
    toggle = demo.phase(n, 0.6, 0.7)
    _chip(cv, GRID_X, 52, 58, toggle < 0.5, (demo.ACCENT, demo.TEAL))
    _chip(cv, GRID_X + 70, 52, 44, toggle >= 0.5, (demo.ACCENT,))
    before = masonry_layout(HEIGHTS, COLS, GRID_X, GRID_Y, GRID_W, GAP)
    kept = masonry_layout([h for h, k in zip(HEIGHTS, KEEP) if k], COLS, GRID_X, GRID_Y, GRID_W, GAP)
    it = iter(kept)
    after = [next(it) if k else None for k in KEEP]
    for i, item in enumerate(reflow(before, after, demo.phase(n, 0.7, 2.3))):
        if item is None:
            continue
        box, alpha, scale = item
        if alpha <= 0:
            continue
        cx, cy = box.x + box.w / 2, box.y + box.h / 2
        demo.card(cv, cx, cy, w=box.w, h=box.h, color=demo.ACCENT if KEEP[i] else demo.TEAL,
                  alpha=alpha, scale=scale)


CAPABILITY = Capability(
    id='masonry-reflow',
    name='Masonry reflow',
    family='ui',
    group='Layout & lists',
    aliases=('waterfall layout reflow', 'staggered grid reflow', 'masonry grid animation'),
    definition='Cards of uneven heights stacked in columns slide to their newly packed spots when some '
               'are filtered away or the columns change, so each column closes up smoothly.',
    phrasings=('when I filter the photo wall, the leftover cards should glide into place',
               'animate the masonry layout rearranging itself instead of snapping',
               'the waterfall of cards repacks smoothly when the column count changes'),
    related=('grid-reflow-shuffle', 'swiss-grid-slide', 'grid-diagonal-stagger', 'shape-stacking-drop',
             'treemap-re-layout', 'mograph-grid-flip'),
    api=('videobuilder.capabilities.ui.masonry_reflow.reflow',
         'videobuilder.capabilities.ui.masonry_reflow.masonry_layout'),
    demo=lambda: demo.film(draw),
)

"""Treemap re-layout: a treemap whose values change, every rectangle growing,
shrinking and sliding at once so the panel stays exactly tiled while it
repacks to the new numbers."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def treemap_layout(values, x, y, w, h, gap=0):
    """The box (x, y, w, h) tiled into one `vb.Box` per value, each with area
    in proportion to its value (after `gap` px gutters), in list order. The
    items are halved by count, recursively, and each half cut across the
    longer side of its box, so the same count and box always give the same
    arrangement and the tiles move continuously as the values change."""
    out = [None] * len(values)
    if values:
        _split(0, len(values), x, y, w, h, out, [max(v, 0) for v in values], gap)
    return out


def _split(lo, hi, x, y, w, h, out, values, gap, shape=None):
    # `shape` is the node's box under equal values: it alone picks each cut's direction
    shape = shape or (w, h)
    if hi - lo == 1:
        out[lo] = vb.Box(x, y, max(w, 0), max(h, 0))
        return
    mid = (lo + hi) // 2
    total = sum(values[lo:hi]) or 1
    t = sum(values[lo:mid]) / total
    k = (mid - lo) / (hi - lo)
    sw, sh = shape
    if sw >= sh:
        a = (w - gap) * t
        _split(lo, mid, x, y, a, h, out, values, gap, (sw * k, sh))
        _split(mid, hi, x + a + gap, y, w - gap - a, h, out, values, gap, (sw * (1 - k), sh))
    else:
        a = (h - gap) * t
        _split(lo, mid, x, y, w, a, out, values, gap, (sw, sh * k))
        _split(mid, hi, x, y + a + gap, w, h - gap - a, out, values, gap, (sw, sh * (1 - k)))


def treemap_relayout(before, after, p, x, y, w, h, gap=0, ease=vb.ease_in_out_quart):
    """The treemap of `treemap_layout` at progress `p` (0 -> 1) of a change of
    data from `before` to `after` (equal-length value lists): the values are
    eased across and the layout recomputed, so the tiles resize and slide
    together and never overlap or leave holes. Returns `(boxes, values)`, the
    boxes and the in-between values (for labels that count along)."""
    q = ease(vb.clamp01(p))
    values = [a + (b - a) * q for a, b in zip(before, after)]
    return treemap_layout(values, x, y, w, h, gap), values


LABELS = 'ABCDEFGH'
DATA = ((45, 66, 57, 85, 63, 72, 51, 77),
        (92, 38, 74, 41, 30, 96, 66, 28),
        (40, 84, 30, 79, 88, 47, 70, 52))
COLOURS = (demo.ACCENT, '#f2b45a', '#3a7bd5', demo.TEAL)
PANEL = (120, 96, 720, 384)
CHANGES = ((0.35, 1.25), (1.75, 2.65))


def draw(n, cv):
    before, after, p = DATA[0], DATA[1], demo.phase(n, *CHANGES[0])
    if n / demo.FPS >= CHANGES[1][0]:
        before, after, p = DATA[1], DATA[2], demo.phase(n, *CHANGES[1])
    boxes, values = treemap_relayout(before, after, p, *PANEL, gap=6)
    tag, num = demo.mono(18, 600), demo.font(30, 800)
    vb.text.draw(cv, ['A–H'], tag, PANEL[0], 52, demo.MUTED)
    total = f'{round(sum(values))}'
    tw, _ = vb.text.block_size([total], num)
    vb.text.draw(cv, [total], num, PANEL[0] + PANEL[2] - tw, 44, demo.INK)
    for i, (b, v) in enumerate(zip(boxes, values)):
        cv.rect(b.x, b.y, b.w, b.h, COLOURS[i % len(COLOURS)], radius=6)
        cv.mark(f'tile-{LABELS[i]}', b.x, b.y, b.w, b.h)
        with cv.clip(b.x, b.y, b.w, b.h, radius=6):
            vb.text.draw(cv, [LABELS[i]], tag, b.x + 12, b.y + 10, demo.BG)
            s = f'{round(v)}'
            sw, sh = vb.text.block_size([s], num)
            vb.text.draw(cv, [s], num, b.x + b.w - sw - 12, b.y + b.h - sh - 8, demo.BG)
    run = (n / demo.FPS) / demo.SECONDS
    cv.rect(PANEL[0], PANEL[1] + PANEL[3] + 22, PANEL[2], 3, demo.LINE)
    cv.rect(PANEL[0], PANEL[1] + PANEL[3] + 22, PANEL[2] * run, 3, demo.ACCENT)


CAPABILITY = Capability(
    id='treemap-re-layout',
    name='Treemap re-layout',
    family='broadcast',
    group='Charts',
    aliases=('treemap transition', 'rectangle rearrange', 'animated treemap'),
    definition='A treemap takes on new numbers and every tile resizes and slides at the same time, '
               'so the panel repacks into the new proportions without ever breaking apart.',
    phrasings=('animate the treemap when the data updates instead of redrawing it',
               'make the blocks of the area chart grow and shrink into their new sizes',
               'show the market-share boxes reshuffling smoothly to next quarter\'s figures'),
    related=('recursive-tree', 'org-chart-grow', 'decision-tree-branch-growth',
             'recursive-rectangle-subdivision', 'tangram-rearrangement', 'grid-reflow-shuffle'),
    api=('videobuilder.capabilities.broadcast.treemap_re_layout.treemap_relayout',
         'videobuilder.capabilities.broadcast.treemap_re_layout.treemap_layout'),
    demo=lambda: demo.film(draw),
)

"""Reorder List Shuffle: one row of a list is picked up and dragged to a new
place; the rows it passes slide out of its way, one slot each, so a gap is
always open where it will drop."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ROW = '#1d1f26'
ROW_LIFTED = '#272a33'
PANEL = '#18191f'


def _smooth(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def reorder_slots(count, src, d, window=0.6):
    """Where each of `count` rows sits, in slots (row 0 at 0.0), while row
    `src` is dragged to slot position `d` (a float; `src` at rest). A row
    below `src` moves up one slot as `d` passes its upper half-way line, a
    row above moves down one as `d` passes its lower one, each easing across
    `window` of a slot, so the rows always leave a gap under the dragged
    one. Returns a list indexed by original row; the dragged row is `d`."""
    out = []
    for i in range(count):
        if i == src:
            out.append(float(d))
        elif i > src:
            out.append(i - _smooth((d - (i - 0.5)) / window + 0.5))
        else:
            out.append(i + _smooth(((i + 0.5) - d) / window + 0.5))
    return out


def draw_reorder(cv, count, src, d, x, y, w, row_h, draw_row, spacing=12, lift=0.0, nudge=8, radius=10):
    """Draw a `count`-row list from its top-left (x, y), `w` wide, rows
    `row_h` tall and `spacing` apart, while row `src` is dragged to slot `d`
    (see `reorder_slots`). `draw_row(cv, i, box, lifted)` draws row `i`
    (its original index) into `box`; `lifted` is True for the dragged row.
    `lift` (0 -> 1) raises the dragged row: a shadow, a slight grow and a
    `nudge` to the right, drawn above the rest. Returns each row's Box."""
    pitch = row_h + spacing
    boxes = [vb.Box(x, y + s * pitch, w, row_h) for s in reorder_slots(count, src, d)]
    for i, b in enumerate(boxes):
        if i != src:
            draw_row(cv, i, b, False)
    b = boxes[src]
    k = 1 + 0.035 * lift
    lw, lh = w * k, row_h * k
    lifted = vb.Box(b.x + nudge * lift - (lw - w) / 2, b.y - (lh - row_h) / 2, lw, lh)
    if lift > 0:
        cv.shadow(*lifted, radius=radius, dy=10 * lift, blur=22 * lift, color=(0, 0, 0, 0.55 * lift))
    draw_row(cv, src, lifted, lift > 0)
    boxes[src] = lifted
    return boxes


def _row(cv, i, b, lifted, hero=1):
    hot = i == hero
    cv.rect(*b, ROW_LIFTED if lifted else ROW, radius=10)
    s = b.h * 0.4
    cv.rect(b.x + 18, b.y + (b.h - s) / 2, s, s, '#8b8ff7' if hot else demo.LINE, radius=5)
    tx = b.x + 18 + s + 16
    cv.rect(tx, b.y + b.h * 0.33, b.w * (0.32 if hot else 0.22 + 0.03 * i), 6,
            demo.INK if hot else demo.MUTED, radius=3, alpha=1 if hot else 0.6)
    cv.rect(tx, b.y + b.h * 0.56, b.w * 0.16, 5, demo.MUTED, radius=2.5, alpha=0.4)
    for k in (-1, 0, 1):  # the drag grip
        demo.dot(cv, b.x + b.w - 24, b.y + b.h / 2 + k * 6, 2, color=demo.MUTED, alpha=0.7)
    cv.mark(f'row-{i}', *b)


def _cursor(cv, x, y, s=1.0):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]
    c = cv.ctx
    c.new_path()
    for j, (px, py) in enumerate(pts):
        (c.move_to if j == 0 else c.line_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill_preserve()
    c.set_source_rgba(0, 0, 0, 1)
    c.set_line_width(2)
    c.stroke()


def draw(n, cv):
    count, src, dst = 5, 1, 3
    w, row_h, spacing = 440, 64, 10
    x = (demo.W - w) / 2
    y = (demo.H - (count * row_h + (count - 1) * spacing)) / 2
    cv.rect(x - 12, y - 12, w + 24, count * row_h + (count - 1) * spacing + 24, PANEL, radius=18)
    lift = vb.ease_out_quint(demo.phase(n, 0.45, 0.75)) - vb.ease_out_quint(demo.phase(n, 2.15, 2.45))
    d = src + (dst - src) * vb.ease_in_out_quart(demo.phase(n, 0.75, 2.05))
    boxes = draw_reorder(cv, count, src, d, x, y, w, row_h, _row, spacing=spacing, lift=lift)
    b = boxes[src]
    gx, gy = b.x + b.w - 22, b.y + b.h / 2 + 3
    home = 1 - vb.ease_out_quint(demo.phase(n, 0.0, 0.45))  # the pointer comes to the grip, then rides it
    _cursor(cv, gx + 80 * home, gy + 40 * home, s=0.7)


TECHNIQUE = Technique(
    id='reorder-list-shuffle',
    name='Reorder list shuffle',
    family='ui',
    group='Gestures & drag',
    aliases=('sortable list', 'drag reorder', 'drag to reorder'),
    definition='A row is lifted out of a list and dragged to a new position while the rows it passes '
               'glide aside one by one, keeping an empty slot open beneath it until it drops in.',
    phrasings=('drag an item down the list and the others make room for it',
               'show someone reordering a list by dragging a row',
               'pick up a list item and move it, with the rest shuffling to fill in'),
    related=('sorted-bar-reorder', 'grid-reflow-shuffle', 'letter-sort-animation', 'leaderboard-row-swap',
             'letter-roll', 'infinite-scroll-append'),
    api=('videobuilder.techniques.ui.reorder_list_shuffle.draw_reorder',
         'videobuilder.techniques.ui.reorder_list_shuffle.reorder_slots'),
    demo=lambda: demo.film(draw),
)

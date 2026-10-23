"""Grid Reflow Shuffle: words sit one per cell of a grid, then trade cells,
each gliding along a gentle arc to its new place so the layout rearranges
while every word stays upright and readable."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def reflow(cells, orders, p, stagger=0.6, bow=0.5, ease=vb.ease_in_out_quart):
    """Where each item is at progress `p` (0 -> 1) through a run of layouts,
    as `(x, y)` centres. `cells` are the grid's Boxes (e.g. `Box.grid`);
    `orders` is two or more layouts, each giving every item's cell index
    (`orders[k][i]` is item i's cell in layout k). The run splits evenly
    into one leg per change of layout; within a leg the moves set off one
    after another across the first `stagger` of it (the two words of a swap
    leave together), and each one bows sideways by `bow` of its travel so the
    pair pass on opposite sides, not through each other. Layouts whose legs
    swap pairs within a row or within a column keep every word clear."""
    legs = len(orders) - 1
    if legs < 1:
        raise ValueError('reflow needs at least two layouts')
    t = vb.clamp01(p) * legs
    leg = min(int(t), legs - 1)
    local = t - leg
    src, dst = orders[leg], orders[leg + 1]
    n = len(src)
    # moves set off in reading order of the first cell they touch, so the
    # two words of a swap leave together and pass on opposite sides
    keys = sorted({min(src[i], dst[i]) for i in range(n) if src[i] != dst[i]})
    out = []
    for i in range(n):
        a, b = cells[src[i]], cells[dst[i]]
        ax, ay = a.x + a.w / 2, a.y + a.h / 2
        bx, by = b.x + b.w / 2, b.y + b.h / 2
        k = keys.index(min(src[i], dst[i])) if src[i] != dst[i] else 0
        start = stagger * k / max(1, len(keys) - 1)
        q = ease(vb.clamp01((local - start) / (1 - stagger)))
        # bow perpendicular to the straight line, peaking mid-move
        dx, dy = bx - ax, by - ay
        lift = 4 * q * (1 - q) * bow
        out.append((ax + dx * q - dy * lift, ay + dy * q + dx * lift))
    return out


def draw_grid_shuffle(cv, words, font, cells, orders, p, color, accent=None, **kw):
    """Draw `words` at progress `p` through `orders` (see `reflow`), each
    centred on its current position. `accent` maps word index -> colour for
    words to pick out. `kw` goes to `reflow`. Returns the positions."""
    at = reflow(cells, orders, p, **kw)
    for i, (word, (x, y)) in enumerate(zip(words, at)):
        demo.word(cv, word, x, y, font=font, color=(accent or {}).get(i, color))
    return at


WORDS = ('SHAPE', 'SPACE', 'SHIFT', 'TYPE', 'GRID', 'FLOW')
# first leg swaps neighbours within each row, the second within columns
ORDERS = ((0, 1, 2, 3, 4, 5),
          (0, 2, 1, 3, 5, 4),
          (3, 2, 4, 0, 5, 1))


def draw(n, cv):
    box = vb.Box(130, 100, demo.W - 260, demo.H - 200)
    cells = box.grid(3, 2)
    for c in cells[1:3]:
        cv.line(c.x, box.y, c.x, box.y + box.h, demo.LINE, width=1.5)
    cv.line(box.x, cells[3].y, box.x + box.w, cells[3].y, demo.LINE, width=1.5)
    p = 0.5 * demo.phase(n, 0.25, 1.4) + 0.5 * demo.phase(n, 1.9, 2.85)
    at = draw_grid_shuffle(cv, WORDS, demo.font(52, 800), cells, ORDERS, p, demo.INK, accent={5: demo.ACCENT})
    for x, y in at:
        cv.mark('word', x - 80, y - 30, 160, 60)


CAPABILITY = Capability(
    id='grid-reflow-shuffle',
    name='Grid reflow shuffle',
    family='typography',
    group='Layout and poster',
    aliases=('typographic grid shuffle', 'tile word reorder', 'word grid swap'),
    definition='Words laid out one to a grid cell swap places, each sliding along a soft curve '
               'to its new cell while staying level and legible.',
    phrasings=('the words in the grid shuffle around into a new order',
               'rearrange the type layout with the words gliding to new spots',
               'swap the words between the cells of the poster grid'),
    related=('letter-sort-animation', 'reorder-list-shuffle', 'letter-roll', 'masonry-reflow',
             'word-carousel-rotate', 'layout-animation-flip'),
    api=('videobuilder.capabilities.typography.grid_reflow_shuffle.reflow',
         'videobuilder.capabilities.typography.grid_reflow_shuffle.draw_grid_shuffle'),
    demo=lambda: demo.film(draw),
)

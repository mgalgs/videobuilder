"""Grid Reflow Shuffle: words sit one per cell of a grid, then trade cells,
each gliding along a gentle arc to its new place so the layout rearranges
while every word stays upright and readable."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def reflow(cells, orders, p, stagger=0.35, bow=0.18, ease=vb.ease_in_out_quart):
    """Where each item is at progress `p` (0 -> 1) through a run of layouts,
    as `(x, y)` centres. `cells` are the grid's Boxes (e.g. `Box.grid`);
    `orders` is two or more layouts, each giving every item's cell index
    (`orders[k][i]` is item i's cell in layout k). The run splits evenly
    into one leg per change of layout; within a leg items start one after
    another across the first `stagger` of it, and each one bows sideways by
    `bow` of its travel so crossing words pass beside, not through, each other."""
    legs = len(orders) - 1
    if legs < 1:
        raise ValueError('reflow needs at least two layouts')
    t = vb.clamp01(p) * legs
    leg = min(int(t), legs - 1)
    local = t - leg
    src, dst = orders[leg], orders[leg + 1]
    n = len(src)
    out = []
    for i in range(n):
        a, b = cells[src[i]], cells[dst[i]]
        ax, ay = a.x + a.w / 2, a.y + a.h / 2
        bx, by = b.x + b.w / 2, b.y + b.h / 2
        start = stagger * i / max(1, n - 1)
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
ORDERS = ((0, 1, 2, 3, 4, 5),
          (4, 0, 5, 1, 3, 2),
          (2, 3, 1, 5, 0, 4))


def draw(n, cv):
    box = vb.Box(130, 100, demo.W - 260, demo.H - 200)
    cells = box.grid(3, 2)
    for c in cells[1:3]:
        cv.line(c.x, box.y, c.x, box.y + box.h, demo.LINE, width=1.5)
    cv.line(box.x, cells[3].y, box.x + box.w, cells[3].y, demo.LINE, width=1.5)
    p = 0.5 * demo.phase(n, 0.35, 1.35) + 0.5 * demo.phase(n, 1.7, 2.7)
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

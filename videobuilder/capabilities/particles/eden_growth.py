"""Eden Growth: a cluster grows one grid cell at a time, each new cell picked
at random from the empty cells touching it, so it swells into a round blob
whose rim stays ragged and restless."""
import functools
import random

from .. import _demo as demo
from ..schema import Capability


@functools.lru_cache(maxsize=16)
def eden_order(cols, rows, count, seed=0, start=None):
    """The first `count` cells of an Eden cluster on a `cols` x `rows` grid,
    as a tuple of `(col, row)` in the order they join. It starts from
    `start` (default the centre); each step adds a cell chosen uniformly at
    random from the empty cells next to the cluster (4-neighbours). Growth
    stops early if the grid fills. The same arguments give the same order."""
    rng = random.Random(seed)
    first = start or (cols // 2, rows // 2)
    taken = {first}
    order = [first]
    border, on_border = [], set()

    def touch(c, r):
        for nc, nr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            cell = (nc, nr)
            if 0 <= nc < cols and 0 <= nr < rows and cell not in taken and cell not in on_border:
                on_border.add(cell)
                border.append(cell)

    touch(*first)
    while len(order) < count and border:
        i = rng.randrange(len(border))
        border[i], border[-1] = border[-1], border[i]
        cell = border.pop()
        on_border.discard(cell)
        taken.add(cell)
        order.append(cell)
        touch(*cell)
    return tuple(order)


def eden_growth(cv, x, y, cols, rows, size, p, count=None, seed=0, color=demo.INK, fresh=demo.ACCENT,
                glow=0.06, gap=0.12):
    """Draw an Eden cluster on the grid whose top-left is (x, y), cells
    `size` apart, grown to progress `p` (0 -> 1 of `count` cells; `count`
    defaults to about a third of the grid). Settled cells are `color`; the
    newest `glow` fraction of `count` are tinted `fresh`, fading as newer
    cells pile on, which lights up the growing rim. `gap` is the gutter
    between cells as a fraction of `size`. Returns how many cells are shown."""
    count = count or cols * rows // 3
    order = eden_order(cols, rows, count, seed)
    shown = max(1, min(len(order), round(len(order) * max(0.0, min(1.0, p)))))
    side = size * (1 - gap)
    window = max(1.0, glow * len(order))
    for i in range(shown):
        c, r = order[i]
        cx, cy = x + c * size, y + r * size
        heat = 1 - (shown - 1 - i) / window
        if heat > 0:
            cv.rect(cx, cy, side, side, color, alpha=1 - heat)
            cv.rect(cx, cy, side, side, fresh, alpha=heat)
        else:
            cv.rect(cx, cy, side, side, color)
    return shown


COLS, ROWS, SIZE = 120, 76, 7


def draw(n, cv):
    x, y = (demo.W - COLS * SIZE) / 2, (demo.H - ROWS * SIZE) / 2
    p = demo.phase(n, 0.2, 2.8) ** 1.4  # cells per frame grows with the rim, so the radius widens steadily
    eden_growth(cv, x, y, COLS, ROWS, SIZE, p, count=2300, seed=0)
    cv.mark('cluster', x, y, COLS * SIZE, ROWS * SIZE)


CAPABILITY = Capability(
    id='eden-growth',
    name='Eden growth',
    family='particles',
    group='Reaction & growth',
    aliases=('Eden model', 'random frontier growth', 'Eden cluster'),
    definition='A blob of square cells grows outward from one seed as new cells are added one by one '
               'at random spots along its edge, filling in solid with a rough, jittery outline.',
    phrasings=('grow a blob cell by cell from the middle like a bacteria colony',
               'a pixel cluster that spreads out at random from its edges',
               'show something growing organically outward on a grid'),
    related=('lenia', 'voronoi-relaxation', 'conway-s-game-of-life', 'circle-packing', 'voronoi-cells',
             'morphing-blob'),
    api=('videobuilder.capabilities.particles.eden_growth.eden_growth',
         'videobuilder.capabilities.particles.eden_growth.eden_order'),
    demo=lambda: demo.film(draw),
)

"""Sandpile avalanche: grains drop one at a time onto a grid of stacks; any
stack that reaches four tips one grain onto each neighbour, which can tip
them in turn, so a single grain sets off a cascade anywhere from nothing to
most of the pile."""
import random

from .. import _demo as demo
from ..schema import Technique


def sandpile_avalanche(cols, rows, steps, threshold=4, seed=0, fill=None, drop=None, warmup=None):
    """A step-by-step sandpile run on a `cols` x `rows` grid, for animating.

    The pile starts from `fill` (a list of `rows` lists of `cols` heights) or,
    by default, an empty grid with `warmup` grains (default 2 per cell)
    dropped at random and settled, which leaves it poised at the edge of
    tipping. Each step either drops one grain on a cell (when the pile is
    calm) or topples every stack holding `threshold` or more at once: it
    loses `threshold` grains and each of its four neighbours gains one;
    grains pushed off the edge are lost. `drop(rng)` picks the `(col, row)`
    a grain lands on (default: anywhere in the middle half of the grid).

    Returns one state per step, each a dict: `heights` (rows of ints after
    the step), `toppled` (set of `(col, row)` that tipped this step),
    `avalanche` (every cell tipped so far in the current avalanche), `drop`
    (the cell a grain landed on this step, or None), `count` (topples so
    far in the current avalanche) and `sizes` (topple counts of every
    finished avalanche so far, in order).
    """
    rng = random.Random(seed)
    warmup = 2 * cols * rows if warmup is None else warmup
    h = [list(r) for r in fill] if fill is not None else [[0] * cols for _ in range(rows)]
    if drop is None:
        def drop(r):
            return (r.randrange(cols // 4, cols - cols // 4), r.randrange(rows // 4, rows - rows // 4))

    def topple():
        hot = {(x, y) for y in range(rows) for x in range(cols) if h[y][x] >= threshold}
        for x, y in hot:
            h[y][x] -= threshold
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < cols and 0 <= ny < rows:
                    h[ny][nx] += 1
        return hot

    for _ in range(warmup if fill is None else 0):  # grow the pile until it sits at the edge of tipping
        h[rng.randrange(rows)][rng.randrange(cols)] += 1
        while topple():
            pass
    while topple():
        pass
    out, region, count, sizes = [], set(), 0, []
    for _ in range(steps):
        hot = topple()
        landed = None
        if hot:
            region |= hot
            count += len(hot)
        else:
            if count:
                sizes.append(count)
            region, count = set(), 0
            landed = drop(rng)
            h[landed[1]][landed[0]] += 1
        out.append({'heights': [list(r) for r in h], 'toppled': hot, 'avalanche': set(region),
                    'drop': landed, 'count': count, 'sizes': list(sizes)})
    return out


COLS = ROWS = 31
CELL = 14
GX, GY = 110, (demo.H - ROWS * CELL) / 2
SAND = ('#1d1e24', '#36302a', '#5e4c32', '#9a7a42')  # stack heights 0..3, empty to one short of tipping
GLOW = 14  # frames a toppled cell stays tinted, so an avalanche's whole extent reads
_run = []


def _states():
    if not _run:
        _run.extend(sandpile_avalanche(COLS, ROWS, round(demo.SECONDS * demo.FPS), seed=13))
    return _run


def draw(n, cv):
    states = _states()
    n = min(n, len(states) - 1)
    s = states[n]
    last = {}
    for i in range(max(0, n - GLOW), n + 1):
        for c in states[i]['toppled']:
            last[c] = i
    for y, row in enumerate(s['heights']):
        for x, v in enumerate(row):
            px, py = GX + x * CELL, GY + y * CELL
            cv.rect(px + 1, py + 1, CELL - 2, CELL - 2, SAND[min(v, 3)], radius=3)
            if (x, y) in last:
                age = n - last[(x, y)]
                cv.rect(px + 1, py + 1, CELL - 2, CELL - 2, demo.ACCENT, radius=3,
                        alpha=1.0 if age == 0 else 0.7 * (1 - age / (GLOW + 1)))
    cv.mark('pile', GX, GY, COLS * CELL, ROWS * CELL)
    for i in range(max(0, n - 6), n + 1):  # the grain that started it: a ring that shrinks onto its cell
        d = states[i]['drop']
        if d:
            k = (n - i) / 6
            cv.arc(GX + (d[0] + 0.5) * CELL, GY + (d[1] + 0.5) * CELL, CELL * (1.8 - 1.2 * k), 0, 6.3,
                   demo.INK, width=3, alpha=1 - k)

    # each avalanche's size as a bar, the running one in accent
    bx, base, top = 600, demo.H - 90, 120
    sizes = s['sizes'] + ([s['count']] if s['toppled'] else [])
    demo.word(cv, 'avalanche sizes', bx + 130, top - 50, size=26, color=demo.MUTED, weight=700)
    cv.line(bx, base, bx + 260, base, demo.LINE, width=2)
    bw = 26
    for i, v in enumerate(sizes[-8:]):
        hgt = (base - top) * min(1.0, v / 200)
        running = s['toppled'] and i == len(sizes[-8:]) - 1
        cv.rect(bx + 6 + i * (bw + 6), base - max(hgt, 3), bw, max(hgt, 3),
                demo.ACCENT if running else SAND[3], radius=4)


TECHNIQUE = Technique(
    id='sandpile-avalanche',
    name='Sandpile avalanche',
    family='particles',
    group='Sand & granular',
    aliases=('Bak-Tang-Wiesenfeld sandpile', 'abelian sandpile', 'self-organized criticality'),
    definition='Grains land one by one on a grid of little stacks, and any stack that grows too tall spills '
               'onto its neighbours, setting off chain-reaction slides that are sometimes tiny and sometimes huge.',
    phrasings=('drop sand grains one at a time and show the cascades they trigger',
               'a grid that keeps piling up until it collapses in chain reactions of random size',
               'self-organized criticality animation with toppling cells'),
    related=('falling-sand', 'dust-motes', 'film-grain', 'koch-snowflake', 'rigid-body-pile', 'snowfall'),
    api=('videobuilder.techniques.particles.sandpile_avalanche.sandpile_avalanche',),
    demo=lambda: demo.film(draw),
)

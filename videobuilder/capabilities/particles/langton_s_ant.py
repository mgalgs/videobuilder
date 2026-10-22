"""Langton's Ant: one ant on a grid of cells turns right on a blank cell and
left on a filled one, flipping each cell as it leaves; a few hundred steps of
tidy shapes turn into a long chaotic blob, until it suddenly builds a
straight diagonal highway out of the mess."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

HEADINGS = ((0, -1), (1, 0), (0, 1), (-1, 0))  # up, right, down, left: turning right is +1


_RUNS = {}  # rule -> the longest walk so far, extended on demand: (path, headings, states, [x, y, h])


def _walk(steps, rule):
    """The ant's first `steps + 1` positions and its heading index into
    `HEADINGS` after `steps` steps. One run per `rule` is kept and extended,
    so a film asking for a growing step count every frame walks it once."""
    path, headings, states, at = _RUNS.setdefault(rule, ([(0, 0)], [0], {}, [0, 0, 0]))
    x, y, h = at
    while len(path) <= steps:
        s = states.get((x, y), 0)
        h = (h + (1 if rule[s] == 'R' else -1)) % 4
        states[(x, y)] = (s + 1) % len(rule)
        x, y = x + HEADINGS[h][0], y + HEADINGS[h][1]
        path.append((x, y))
        headings.append(h)
    at[:] = x, y, h
    return path[:steps + 1], headings[steps]


def langton_ant(steps, rule='RL'):
    """The grid after `steps` steps of the ant, as `(cells, (x, y), heading)`:
    `cells` maps each non-blank (x, y) to its state (1 for filled in the
    classic two-colour `rule='RL'`), the ant starts at (0, 0) facing up (y
    grows downward) and `heading` is its final (dx, dy). `rule` gives the
    turn for each state in turn, so `'RLR'` or `'LLRR'` are the multi-colour
    variants."""
    steps = max(0, int(steps))
    path, h = _walk(steps, rule)
    visits = {}
    for cell in path[:-1]:
        visits[cell] = visits.get(cell, 0) + 1
    cells = {c: v % len(rule) for c, v in visits.items() if v % len(rule)}
    return cells, path[-1], HEADINGS[h]


def draw_langton_ant(cv, steps, cx, cy, cell=8, rule='RL', colors=(demo.INK,), ant=demo.ACCENT,
                     grid=demo.LINE, cols=None, rows=None):
    """Draw the grid after `steps` steps with the ant's start cell centred at
    (cx, cy), `cell` px a side. Filled cells use `colors[state - 1]`, the ant
    is a `ant` square with a nose on its heading side, and `grid` (if set)
    rules faint lines over `cols` x `rows` cells around the start (default:
    the whole canvas). Returns the Box of the filled cells and the ant."""
    cells, (ax, ay), (hx, hy) = langton_ant(steps, rule)
    ox, oy = cx - cell / 2, cy - cell / 2
    if grid:
        W, H = cv.width, cv.height
        x0, x1 = (ox - cols // 2 * cell, ox + (cols - cols // 2) * cell) if cols else (ox % cell - cell, W)
        y0, y1 = (oy - rows // 2 * cell, oy + (rows - rows // 2) * cell) if rows else (oy % cell - cell, H)
        x = x0
        while x <= x1 + 0.5:
            cv.line(x, y0, x, y1, grid, width=1, alpha=0.6)
            x += cell
        y = y0
        while y <= y1 + 0.5:
            cv.line(x0, y, x1, y, grid, width=1, alpha=0.6)
            y += cell
    gap = 1 if cell >= 5 else 0
    for (x, y), s in cells.items():
        cv.rect(ox + x * cell + gap / 2, oy + y * cell + gap / 2, cell - gap, cell - gap,
                colors[(s - 1) % len(colors)])
    px, py = ox + ax * cell, oy + ay * cell
    cv.rect(px - cell * 0.15, py - cell * 0.15, cell * 1.3, cell * 1.3, ant)
    nose = cell * 0.35
    cv.rect(px + cell / 2 + hx * cell * 0.75 - nose / 2, py + cell / 2 + hy * cell * 0.75 - nose / 2,
            nose, nose, ant)
    xs = [x for x, _ in cells] + [ax]
    ys = [y for _, y in cells] + [ay]
    return vb.Box(ox + min(xs) * cell, oy + min(ys) * cell,
                  (max(xs) - min(xs) + 1) * cell, (max(ys) - min(ys) + 1) * cell)


TOTAL = 12000  # past ~10,000 steps the chaos gives way to the highway


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.75)
    steps = round(TOTAL * p ** 3)  # slow at first so the single ant reads, then racing into the highway
    box = draw_langton_ant(cv, steps, demo.W / 2 + 112, demo.H / 2 - 48, cell=8)  # centres the step-12,000 pattern
    cv.mark('ant', *box)
    f = demo.mono(22, 600)
    label = f'step {steps:,}'
    vb.text.draw(cv, [label], f, demo.W - 40 - vb.text.measure(label, f), demo.H - 52, demo.MUTED)


CAPABILITY = Capability(
    id='langton-s-ant',
    name="Langton's ant",
    family='particles',
    group='Cellular automata',
    aliases=('Langton ant', "Langton's ant automaton"),
    definition='A single walker on a grid flips each square it crosses and turns left or right by '
               'that square\'s colour, scribbling a messy blob that eventually shoots off as a straight diagonal road.',
    phrasings=('a little ant walking a grid, flipping squares black and white until it makes a pattern',
               'the cellular automaton where one cell-flipping walker builds a highway out of chaos',
               'a pixel bug that turns and paints tiles as it wanders'),
    related=('ant-colony-pheromone-trails', 'l-system-plant', 'hopalong-attractor', 'penrose-tiling',
             'dashed-line-march', 'thomas-attractor'),
    api=('videobuilder.capabilities.particles.langton_s_ant.draw_langton_ant',
         'videobuilder.capabilities.particles.langton_s_ant.langton_ant'),
    demo=lambda: demo.film(draw),
)

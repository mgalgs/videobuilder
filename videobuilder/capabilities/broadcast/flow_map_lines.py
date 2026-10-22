"""Flow map lines: curved lines run from an origin to its destinations on a
map, each line as thick as the volume it carries, so the heavy routes read
at a glance against the light ones."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def flow_arc(origin, dest, bend=0.25, steps=48):
    """The point list of a gently curved flow from `origin` to `dest`: a
    quadratic curve whose middle bows sideways by `bend` times the distance
    (positive bows to the left of travel, negative to the right)."""
    (x0, y0), (x1, y1) = origin, dest
    dx, dy = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2 - dy * bend, (y0 + y1) / 2 + dx * bend
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1))
    return out


def flow_map_lines(cv, flows, progress, color=demo.TEAL, min_width=2.0, max_width=14.0, bend=0.25,
                   stagger=0.6, beads=None, alpha=1.0):
    """Draw origin-destination flows onto `cv`, each line's width scaled to
    its volume. `flows`: a sequence of `(origin, dest, volume)` with points
    in film px. `progress` 0 -> 1 draws the lines on, one after another in
    the given order; `stagger` is how much of the run is spent starting them
    (0: all at once). Widths run linearly from `min_width` at the smallest
    volume to `max_width` at the largest. `bend`: the sideways bow of each
    curve (see `flow_arc`). `beads`: when given, a running phase (e.g.
    seconds) that sends small bright beads down every finished line, faster
    on heavier lines. Returns one `(dest, reached, width)` per flow, where
    `reached` is that line's own 0 -> 1 progress, for labelling the ends."""
    vols = [v for _, _, v in flows]
    lo, hi = (min(vols), max(vols)) if vols else (0, 0)
    n = len(flows)
    span = max(1e-6, 1 - stagger)
    state = []
    for i, (a, b, v) in enumerate(flows):
        start = stagger * i / (n - 1) if n > 1 else 0.0
        reached = vb.clamp01((progress - start) / span)
        weight = (v - lo) / (hi - lo) if hi > lo else 1.0
        width = min_width + (max_width - min_width) * weight
        state.append((a, b, reached, width, weight))
    # heavy lines underneath, so a thin line crossing one stays visible
    for a, b, reached, width, weight in sorted(state, key=lambda s: -s[3]):
        if reached <= 0:
            continue
        eased = 1 - (1 - reached) ** 3
        pts = flow_arc(a, b, bend)
        shown = vb.paths.reveal(pts, eased)
        vb.paths.draw(cv, shown, '#000000', width=width + 4, alpha=0.25 * alpha)
        vb.paths.draw(cv, shown, color, width=width, alpha=alpha)
        if beads is not None and reached >= 1:
            speed = 0.35 + 0.35 * weight
            for k in range(3):
                f = (beads * speed + k / 3) % 1.0
                x, y = vb.paths.reveal(pts, f)[-1] if f > 0 else pts[0]
                r = max(1.5, width * 0.32)
                cv.sector(x, y, r, 0, 2 * math.pi, '#ffffff', alpha=0.8 * alpha * math.sin(math.pi * f))
    return [(b, reached, width) for a, b, reached, width, _ in state]


# -- demo ------------------------------------------------------------------

HUB = (452, 282)
CITIES = (  # (name, position, volume) in the order their lines draw on
    ('North', (300, 112), 68),
    ('Coast', (668, 120), 31),
    ('Delta', (770, 276), 87),
    ('Ridge', (650, 426), 54),
    ('Basin', (430, 470), 22),
    ('Plains', (230, 400), 76),
    ('Harbor', (170, 220), 42),
)
FLOWS = tuple((HUB, pos, vol) for _, pos, vol in CITIES)

LAND = vb.paths.torn(
    [(140, 150), (250, 70), (420, 92), (560, 64), (720, 92), (830, 190), (812, 320), (850, 410),
     (720, 492), (560, 470), (420, 510), (280, 480), (150, 430), (110, 300)],
    seed=7, amount=10.0, step=4.0)
BORDERS = tuple(vb.paths.jitter(line, seed=i, amount=2.5) for i, line in enumerate((
    [(300, 74), (330, 190), (452, 282)],
    [(452, 282), (600, 230), (826, 220)],
    [(452, 282), (520, 400), (560, 470)],
    [(452, 282), (300, 330), (118, 330)],
)))


def draw(n, cv):
    t = n / demo.FPS
    vb.paths.draw(cv, LAND, '#1d2027', fill=True)
    vb.paths.draw(cv, LAND, demo.LINE, width=2, closed=True)
    for b in BORDERS:
        vb.paths.draw(cv, vb.paths.resample(b, 30), demo.LINE, width=1.5)

    ends = flow_map_lines(cv, FLOWS, demo.phase(n, 0.25, 2.1), beads=t)

    for (name, (x, y), vol), (_, reached, _) in zip(CITIES, ends):
        demo.dot(cv, x, y, 5, color=demo.INK)
        d = math.hypot(x - HUB[0], y - HUB[1])
        lx, ly = x + (x - HUB[0]) / d * 34, y + (y - HUB[1]) / d * 30  # labels sit beyond the line's end
        demo.word(cv, name, lx, ly - 9, size=15, color=demo.MUTED, weight=600)
        if reached > 0.6:
            a = vb.clamp01((reached - 0.6) / 0.4)
            demo.word(cv, str(round(vol * a)), lx, ly + 9, size=15, color=demo.TEAL, weight=800, alpha=a)
    demo.dot(cv, *HUB, 11, color='#f2b632')
    cv.arc(HUB[0], HUB[1], 11, 0, 2 * math.pi, demo.BG, width=3)
    cv.mark('hub', HUB[0] - 11, HUB[1] - 11, 22, 22)

    # the legend: thin line = least volume, thick line = most
    lx, ly = 40, demo.H - 40
    demo.word(cv, '22', lx + 30, ly - 20, size=15, color=demo.MUTED, weight=600)
    demo.word(cv, '87', lx + 100, ly - 20, size=15, color=demo.MUTED, weight=600)
    cv.line(lx, ly, lx + 60, ly, demo.TEAL, width=2)
    cv.line(lx + 70, ly, lx + 130, ly, demo.TEAL, width=14)


CAPABILITY = Capability(
    id='flow-map-lines',
    name='Flow map lines',
    family='broadcast',
    group='Maps',
    aliases=('migration flow lines', 'origin-destination flow', 'flow map'),
    definition='Curved lines grow across a map from a starting place to several others, each one drawn '
               'thicker or thinner according to how much travels along it.',
    phrasings=('show how many people move from this city to the others with lines on a map',
               'draw arrows out from one place whose thickness shows the amount',
               'a map where the routes get fatter the more traffic they carry'),
    related=('streamlines', 'map-route-draw', 'streamgraph-flow', 'line-chart-draw-on', 'sankey-flow',
             'speed-lines'),
    api=('videobuilder.capabilities.broadcast.flow_map_lines.flow_map_lines',
         'videobuilder.capabilities.broadcast.flow_map_lines.flow_arc'),
    demo=lambda: demo.film(draw),
)

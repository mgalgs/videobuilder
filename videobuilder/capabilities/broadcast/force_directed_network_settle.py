"""Force-directed network settle: a node-link chart that starts as a tangled
knot and sorts itself out -- every node pushes the others away, every link
pulls its two ends together, and the whole web drifts, overshoots a little
and comes to rest in an untangled layout."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def force_layout(count, edges, frames, fps=30, center=(demo.W / 2, demo.H / 2), spread=40.0, length=150.0,
                 repel=8000.0, pull=6.0, gravity=0.4, damping=1.5, settle=None, seed=7, substeps=4):
    """Simulate a force-directed layout of `count` nodes joined by `edges`
    (`(a, b)` node-index pairs). Returns one tuple of `count` (x, y)
    positions per frame for `frames` frames at `fps`.

    Nodes start scattered within `spread` px of `center` (seeded by `seed`,
    so tangled but repeatable). Every pair repels with strength `repel`
    (a push that weakens with distance), each edge acts as a spring of rest
    `length` and stiffness `pull`, and `gravity` draws everything back
    towards `center` so the web stays framed. `damping` bleeds off speed;
    `settle` (seconds) optionally ramps the damping up after that time so the
    layout comes fully to rest. Pure: same arguments, same frames, so a
    `draw(n, cv)` can index the result by frame."""
    return _simulate(int(count), tuple((int(a), int(b)) for a, b in edges), int(frames), float(fps),
                     (float(center[0]), float(center[1])), float(spread), float(length), float(repel),
                     float(pull), float(gravity), float(damping), None if settle is None else float(settle),
                     int(seed), int(substeps))


@lru_cache(maxsize=16)
def _simulate(count, edges, frames, fps, center, spread, length, repel, pull, gravity, damping, settle, seed,
              substeps):
    rng = random.Random(seed)
    cx, cy = center
    xs, ys = [], []
    for _ in range(count):
        a, r = rng.uniform(0, 2 * math.pi), spread * math.sqrt(rng.random())
        xs.append(cx + r * math.cos(a))
        ys.append(cy + r * math.sin(a))
    vx, vy = [0.0] * count, [0.0] * count
    dt = 1.0 / fps / substeps
    out = []
    for f in range(frames):
        out.append(tuple(zip(xs, ys)))
        for s in range(substeps):
            t = (f + s / substeps) / fps
            drag = damping if settle is None or t < settle else damping * (1 + 4 * (t - settle))
            fx = [gravity * (cx - x) for x in xs]
            fy = [gravity * (cy - y) for y in ys]
            for i in range(count):
                for j in range(i + 1, count):
                    dx, dy = xs[i] - xs[j], ys[i] - ys[j]
                    k = repel / max(dx * dx + dy * dy, 25.0)
                    fx[i] += dx * k
                    fy[i] += dy * k
                    fx[j] -= dx * k
                    fy[j] -= dy * k
            for a, b in edges:
                dx, dy = xs[b] - xs[a], ys[b] - ys[a]
                d = max(math.hypot(dx, dy), 1e-6)
                k = pull * (d - length) / d
                fx[a] += dx * k
                fy[a] += dy * k
                fx[b] -= dx * k
                fy[b] -= dy * k
            keep = math.exp(-drag * dt)
            for i in range(count):
                vx[i] = (vx[i] + fx[i] * dt) * keep
                vy[i] = (vy[i] + fy[i] * dt) * keep
                xs[i] += vx[i] * dt
                ys[i] += vy[i] * dt
    return tuple(out)


def draw_graph(cv, points, edges, labels=(), r=22, colors=(demo.TEAL, demo.ACCENT), line=demo.MUTED, width=2.5):
    """Draw one frame of a node-link chart: `edges` as straight lines between
    `points`, then each node as a dot (alternating `colors`) with its label
    from `labels` centred on it."""
    for a, b in edges:
        (x1, y1), (x2, y2) = points[a], points[b]
        cv.line(x1, y1, x2, y2, line, width=width)
    f = demo.font(round(r * 0.9), 800)
    for i, (x, y) in enumerate(points):
        demo.dot(cv, x, y, r, color=colors[i % len(colors)])
        if i < len(labels):
            tw, th = vb.text.block_size([labels[i]], f)
            vb.text.draw(cv, [labels[i]], f, x - tw / 2, y - th / 2, demo.BG)
        cv.mark(f'node{i}', x - r, y - r, 2 * r, 2 * r)


LABELS = tuple('ABCDEFGHIJ')
EDGES = ((0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (2, 6), (2, 7), (3, 8), (3, 9), (4, 5), (6, 7),
         (8, 9))  # a hub, three branches, each closing into a triangle


def draw(n, cv):
    frames = force_layout(len(LABELS), EDGES, round(demo.SECONDS * demo.FPS), fps=demo.FPS, settle=1.6, seed=1)
    hold = round(0.3 * demo.FPS)  # a beat on the tangle before the forces kick in
    draw_graph(cv, frames[max(0, n - hold)], EDGES, LABELS)


TECHNIQUE = Technique(
    id='force-directed-network-settle',
    name='Force-directed network settle',
    family='broadcast',
    group='Charts',
    aliases=('force graph', 'node-link layout', 'force-directed layout', 'spring layout'),
    definition='A network of dots and connecting lines starts bunched up and tangled, then drifts apart '
               'and untangles as the dots push each other away and the lines tug linked dots together, '
               'easing to rest in a tidy layout.',
    phrasings=('a network graph that untangles itself and settles into place',
               'nodes and links spreading out like a physics simulation until they stop moving',
               'animate a connection map relaxing into a clean layout'),
    related=('connector-network', 'springs-network', 'hub-and-spoke-spread', 'social-force-crowd',
             'chain-follow-through', 'settle'),
    api=('videobuilder.techniques.broadcast.force_directed_network_settle.force_layout',
         'videobuilder.techniques.broadcast.force_directed_network_settle.draw_graph'),
    demo=lambda: demo.film(draw),
)

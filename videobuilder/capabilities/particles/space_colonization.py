"""Space colonization: a cloud of target points pulls a branching network out
of a seed; each branch tip steps toward the targets nearest it and eats the
ones it reaches, so the veins spread until the whole region is filled."""
import functools
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def colonize(attractors, roots, influence=50.0, kill=8.0, step=5.0, max_steps=400):
    """Grow a branch network from `roots` (a list of (x, y)) through the
    point cloud `attractors` (a list of (x, y)).

    Every step, each live attractor finds the nearest node within `influence`;
    each node so chosen grows one new node `step` further along the mean
    direction to its attractors, and attractors within `kill` of a node are
    used up. While nothing is within reach, the newest node heads straight for
    the middle of the cloud (the trunk). Stops when the cloud is used up,
    nothing can grow, or after `max_steps`.

    Returns `(nodes, eaten)`: `nodes` is a list of `(x, y, parent, born)`,
    each parent's index below its child's (roots have parent -1, born 0);
    `eaten[i]` is the step that used up attractor `i` (None if never)."""
    nodes = []
    grid = {}  # cells of side `step`, only for spotting a node grown on top of another
    live = set(range(len(attractors)))
    eaten = [None] * len(attractors)
    best = [(math.inf, -1)] * len(attractors)  # each attractor's nearest node so far: (distance, index)

    def add(x, y, parent, born):
        nodes.append((x, y, parent, born))
        grid.setdefault((int(x // step), int(y // step)), []).append(len(nodes) - 1)

    def crowded(x, y):
        cx, cy = int(x // step), int(y // step)
        return any(math.hypot(nodes[i][0] - x, nodes[i][1] - y) < step * 0.25
                   for gx in (cx - 1, cx, cx + 1) for gy in (cy - 1, cy, cy + 1) for i in grid.get((gx, gy), ()))

    def settle(first, k):
        """Update nearest nodes against nodes `first`.., then use up attractors within `kill`."""
        for a in list(live):
            ax, ay = attractors[a]
            d0, i0 = best[a]
            for i in range(first, len(nodes)):
                d = math.hypot(nodes[i][0] - ax, nodes[i][1] - ay)
                if d < d0:
                    d0, i0 = d, i
            best[a] = (d0, i0)
            if d0 <= kill:
                live.discard(a)
                eaten[a] = k

    for x, y in roots:
        add(x, y, -1, 0)
    settle(0, 0)
    for k in range(1, max_steps + 1):
        if not live:
            break
        pull = {}
        for a in live:
            d, i = best[a]
            if d <= influence:
                ax, ay = attractors[a]
                sx, sy = pull.get(i, (0.0, 0.0))
                pull[i] = (sx + (ax - nodes[i][0]) / d, sy + (ay - nodes[i][1]) / d)
        first = len(nodes)
        if pull:
            for i, (sx, sy) in sorted(pull.items()):
                m = math.hypot(sx, sy)
                if m < 1e-6:
                    continue  # pulled equally both ways: stay put
                x, y = nodes[i][0] + step * sx / m, nodes[i][1] + step * sy / m
                if not crowded(x, y):
                    add(x, y, i, k)
        else:
            mx = sum(attractors[a][0] for a in live) / len(live)
            my = sum(attractors[a][1] for a in live) / len(live)
            i = len(nodes) - 1
            dx, dy = mx - nodes[i][0], my - nodes[i][1]
            d = math.hypot(dx, dy)
            if d > 1e-9:
                add(nodes[i][0] + step * dx / d, nodes[i][1] + step * dy / d, i, k)
        if len(nodes) == first:
            break
        settle(first, k)
    return nodes, eaten


def draw_network(cv, nodes, t, color, width=1.0, thicken=0.5, max_width=8.0, tip=None, tip_r=2.0, alpha=1.0):
    """Draw the part of a `colonize` network grown by (fractional) step `t`:
    every segment born by then, the newest drawn part-way so the growth runs
    smoothly between steps. Each segment is `width` plus `thicken` times the
    square root of the nodes it carries, capped at `max_width`, so the trunk
    swells as the crown fills. `tip` colours the growing ends."""
    shown = [i for i, nd in enumerate(nodes) if nd[3] <= math.ceil(t)]
    load = [0] * len(nodes)
    for i in reversed(shown):
        load[i] += 1
        if nodes[i][3] and nodes[i][2] >= 0:
            load[nodes[i][2]] += load[i]
    has_child = set()
    c = cv.ctx
    c.save()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in shown:
        x, y, parent, born = nodes[i]
        if parent < 0:
            continue
        has_child.add(parent)
        px, py = nodes[parent][0], nodes[parent][1]
        f = vb.clamp01(t - (born - 1))
        cv.line(px, py, px + (x - px) * f, py + (y - py) * f, color,
                width=min(max_width, width + thicken * math.sqrt(load[i])), alpha=alpha)
    c.restore()
    if tip:
        for i in shown:
            if i not in has_child and nodes[i][3] > t - 6:
                x, y, parent, born = nodes[i]
                f = vb.clamp01(t - (born - 1))
                if parent >= 0:
                    px, py = nodes[parent][0], nodes[parent][1]
                    x, y = px + (x - px) * f, py + (y - py) * f
                demo.dot(cv, x, y, tip_r, color=tip, alpha=alpha)


CROWN = (demo.W / 2, 238, 300, 190)  # centre x, y and radii of the region to fill
ROOT = (demo.W / 2, demo.H - 40)


@functools.lru_cache(maxsize=1)
def _grown():
    cx, cy, rx, ry = CROWN
    rnd = random.Random(11)
    pts = []
    while len(pts) < 650:
        u, v = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
        if u * u + v * v <= 1:
            pts.append((cx + u * rx, cy + v * ry))
    nodes, eaten = colonize(pts, [ROOT], influence=55, kill=9, step=5.5)
    return pts, nodes, eaten, max(nd[3] for nd in nodes)


def draw(n, cv):
    pts, nodes, eaten, steps = _grown()
    t = steps * demo.phase(n, 0.3, 2.6)
    for (x, y), k in zip(pts, eaten):
        if k is None or k > t:
            demo.dot(cv, x, y, 1.6, color=demo.TEAL, alpha=0.55)
        elif k > t - 3:
            demo.dot(cv, x, y, 1.6 + (t - k), color=demo.TEAL, alpha=0.55 * (1 - (t - k) / 3))
    draw_network(cv, nodes, t, demo.INK, width=1.0, thicken=0.32, max_width=7, tip=demo.ACCENT, tip_r=2.2)
    demo.dot(cv, *ROOT, 4, color=demo.ACCENT)
    cx, cy, rx, ry = CROWN
    cv.mark('network', cx - rx, cy - ry, 2 * rx, ROOT[1] - (cy - ry))


CAPABILITY = Capability(
    id='space-colonization',
    name='Space colonization',
    family='particles',
    group='Reaction & growth',
    aliases=('Runions tree', 'attractor-driven branching', 'venation growth'),
    definition='Branches sprout from a seed and fork toward a scattered field of target points, '
               'consuming each one they reach until a vein-like network fills the shape.',
    phrasings=('a tree that grows its branches out to fill a shape',
               'veins branching out like a leaf or coral spreading across the area',
               'organic branching that reaches toward scattered dots and eats them'),
    related=('hopalong-attractor', 'recursive-tree', 'decision-tree-branch-growth', 'circle-packing',
             'physarum-slime-mold', 'n-body-gravity'),
    api=('videobuilder.capabilities.particles.space_colonization.colonize',
         'videobuilder.capabilities.particles.space_colonization.draw_network'),
    demo=lambda: demo.film(draw),
)

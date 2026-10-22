"""Flowchart Build: a process diagram assembles itself in the order the
process runs -- the start node pops in, an arrow draws out of it to the next
step, that step pops in, and decisions split into branches that draw at once."""
import math
from collections import deque
from dataclasses import dataclass

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ... import paths
from ..schema import Capability


@dataclass(frozen=True)
class Node:
    """One step of a flowchart, centred at (cx, cy). `shape` is 'box'
    (rounded rectangle), 'pill' (terminal) or 'diamond' (decision)."""
    key: str
    label: str
    cx: float
    cy: float
    w: float = 150
    h: float = 52
    shape: str = 'box'
    color: str = None


@dataclass(frozen=True)
class Edge:
    """An arrow from node `a` to node `b`. `points` overrides the automatic
    elbow route (a list of (x, y), first at `a`, last at `b`); `label` sits
    beside the first hop ("yes", "no")."""
    a: str
    b: str
    label: str = None
    points: tuple = None


def route(na, nb):
    """The default elbow route between two nodes: straight down when they
    share a column, else out of `na`'s side toward `nb`, across, then down
    onto `nb`'s top (up onto its bottom when `nb` sits higher)."""
    down = nb.cy >= na.cy
    end = (nb.cx, nb.cy - nb.h / 2) if down else (nb.cx, nb.cy + nb.h / 2)
    if abs(na.cx - nb.cx) < 1:
        return [(na.cx, na.cy + (na.h if down else -na.h) / 2), end]
    side = 1 if nb.cx > na.cx else -1
    start = (na.cx + side * na.w / 2, na.cy)
    return [start, (nb.cx, na.cy), end]


def schedule(nodes, edges, start=None):
    """When each part of the chart builds, as `{('node', key) | ('edge', i): (t0, t1)}`
    on 0 -> 1. Nodes are ranked by breadth-first distance from `start` (the
    first node by default); a node at depth d builds in slot 2d and every arrow
    leaving it in slot 2d + 1, so sibling branches draw together and a loop
    back to an earlier step draws after the step it leaves."""
    keys = [n.key for n in nodes]
    start = start or keys[0]
    out_of = {k: [] for k in keys}
    for i, e in enumerate(edges):
        out_of[e.a].append(i)
    depth = {start: 0}
    queue = deque([start])
    while queue:
        k = queue.popleft()
        for i in out_of[k]:
            b = edges[i].b
            if b not in depth:
                depth[b] = depth[k] + 1
                queue.append(b)
    last = max(depth.values(), default=0)
    for k in keys:  # unreachable nodes build at the end
        depth.setdefault(k, last + 1)
    slots = {('node', k): 2 * d for k, d in depth.items()}
    slots.update({('edge', i): 2 * depth[e.a] + 1 for i, e in enumerate(edges)})
    total = max(slots.values()) + 1
    return {part: (s / total, (s + 1) / total) for part, s in slots.items()}


def _smooth(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def _arrowhead(cv, tip, prev, color, size):
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    bx, by = tip[0] - ux * size, tip[1] - uy * size
    w = size * 0.55
    paths.draw(cv, [tip, (bx - uy * w, by + ux * w), (bx + uy * w, by - ux * w)], color, fill=True)


def _shape(cv, n, fill, stroke, width):
    x, y = n.cx - n.w / 2, n.cy - n.h / 2
    if n.shape == 'diamond':
        pts = [(n.cx, y), (n.cx + n.w / 2, n.cy), (n.cx, y + n.h), (x, n.cy)]
        cv.shape_shadow(pts, dy=6, blur=18, color=(0, 0, 0, 0.4))
        paths.draw(cv, pts, fill, fill=True)
        paths.draw(cv, pts, stroke, width=width, closed=True)
        return
    radius = n.h / 2 if n.shape == 'pill' else 10
    cv.shadow(x, y, n.w, n.h, radius=radius, dy=6, blur=18, color=(0, 0, 0, 0.4))
    cv.rect(x, y, n.w, n.h, fill, radius=radius)
    if n.shape != 'pill':
        cv.outline(x, y, n.w, n.h, stroke, width=width, radius=radius)


def draw_flowchart(cv, nodes, edges, p, start=None, font=None, label_font=None, line=demo.TEAL,
                   fill='#22252e', ink=demo.INK, accent=demo.ACCENT, width=3, arrow=12):
    """Draw the flowchart `nodes` / `edges` built to progress `p` (0 -> 1).
    Each node pops in (scale overshoot and fade) in its `schedule` slot; each
    arrow then grows along its route with its head riding the tip, and its
    label fades in once the line is half drawn. Pill nodes fill with `accent`
    (or the node's own `color`); boxes and diamonds fill with `fill`, outlined
    in `line`. Returns the schedule so a film can sync cues to it."""
    font = font or kit.font(17, 800)
    label_font = label_font or kit.font(13, 800)
    times = schedule(nodes, edges, start)
    by_key = {n.key: n for n in nodes}
    local = lambda part: vb.clamp01((p - times[part][0]) / (times[part][1] - times[part][0]))  # noqa: E731

    for i, e in enumerate(edges):
        q = _smooth(local(('edge', i)))
        if q <= 0:
            continue
        pts = list(e.points) if e.points else route(by_key[e.a], by_key[e.b])
        drawn = paths.reveal(pts, q)
        if len(drawn) < 2:
            continue
        paths.draw(cv, drawn, line, width=width)
        _arrowhead(cv, drawn[-1], drawn[-2], line, arrow)
        if e.label:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            lw, lh = vb.text.block_size([e.label], label_font)
            horizontal = abs(x1 - x0) > abs(y1 - y0)
            lx = (x0 + x1) / 2 - lw / 2 if horizontal else x0 + 10
            ly = y0 - lh - 8 if horizontal else (y0 + y1) / 2 - lh / 2
            vb.text.draw(cv, [e.label], label_font, lx, ly, line, alpha=vb.clamp01(q * 3 - 1.2))

    for n in nodes:
        q = local(('node', n.key))
        if q <= 0:
            continue
        s = 0.55 + 0.45 * vb.ease_out_back(q)
        with cv.layer(opacity=vb.clamp01(q * 2.5), dx=n.cx * (1 - s), dy=n.cy * (1 - s), scale=s):
            pill = n.shape == 'pill'
            _shape(cv, n, n.color or (accent if pill else fill), line, width)
            tw, th = vb.text.block_size([n.label], font)
            vb.text.draw(cv, [n.label], font, n.cx - tw / 2, n.cy - th / 2, demo.BG if pill else ink)
        cv.mark(n.key, n.cx - n.w / 2, n.cy - n.h / 2, n.w, n.h)
    return times


NODES = (
    Node('start', 'START', 480, 98, w=130, h=44, shape='pill'),
    Node('draft', 'DRAFT', 480, 190),
    Node('review', 'REVIEW?', 480, 302, w=170, h=88, shape='diamond'),
    Node('revise', 'REVISE', 250, 440),
    Node('ship', 'SHIP', 710, 440, w=130, h=44, shape='pill', color=demo.TEAL),
)
EDGES = (
    Edge('start', 'draft'),
    Edge('draft', 'review'),
    Edge('review', 'revise', label='NO'),
    Edge('review', 'ship', label='YES'),
    Edge('revise', 'draft', points=((175, 440), (120, 440), (120, 190), (405, 190))),
)


def draw(n, cv):
    draw_flowchart(cv, NODES, EDGES, demo.phase(n, 0.15, 2.6))


CAPABILITY = Capability(
    id='flowchart-build',
    name='Flowchart build',
    family='broadcast',
    group='Process diagrams',
    aliases=('flow diagram build', 'decision flow reveal', 'process flow animation'),
    definition='A process diagram assembles step by step, each box popping in and an arrow then drawing '
               'from it to the next, with decisions splitting into branches.',
    phrasings=('build the flowchart one step at a time with the arrows drawing in',
               'animate the process diagram so it grows from start to finish',
               'show the decision tree appearing box by box along its arrows'),
    related=('chord-diagram-draw', 'waterfall-build', 'sankey-flow', 'connector-network', 'flow-map-lines',
             'streamgraph-flow'),
    api=('videobuilder.capabilities.broadcast.flowchart_build.draw_flowchart',
         'videobuilder.capabilities.broadcast.flowchart_build.schedule',
         'videobuilder.capabilities.broadcast.flowchart_build.Node',
         'videobuilder.capabilities.broadcast.flowchart_build.Edge',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

"""Connector network: a node-link diagram that builds itself -- one node
appears, then lines reach out from it one at a time, each new node popping in
where its line arrives, until the whole web is drawn."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def network_timing(edges, p, lead=0.12, overlap=0.35):
    """The build state at progress `p` (0 -> 1) of a network whose `edges` are
    `(a, b)` node-index pairs drawn in order. Returns `(nodes, lines)`:
    `nodes` maps each node index to its own 0 -> 1 pop-in progress, `lines`
    is one 0 -> 1 draw fraction per edge. The first edge's start node pops in
    over the first `lead`; each edge then grows from `a` to `b` in its own
    slot (neighbouring slots share `overlap` of their length), and `b` pops
    in as the line lands, unless it is already there."""
    p = vb.clamp01(p)
    k = len(edges)
    if not k:
        return {}, []
    slot = (1 - lead) / (k - (k - 1) * overlap)  # k slots overlapping by `overlap` fill [lead, 1]
    pop = slot * 0.6
    born, lines = {}, []
    for i, (a, b) in enumerate(edges):
        t0 = lead + i * slot * (1 - overlap)
        t1 = t0 + slot * 0.7
        born.setdefault(a, max(0.0, t0 - lead) if i == 0 else t0 - pop)
        born.setdefault(b, t1)
        lines.append(vb.clamp01((p - t0) / (t1 - t0)))
    span = lambda t, length: vb.clamp01((p - t) / length)  # noqa: E731
    nodes = {n: span(t, lead if t == 0 else pop) for n, t in born.items()}
    return nodes, lines


def draw_node(cv, x, y, r, color, amount=1.0, hub=False):
    """One node at (x, y), `amount` 0 -> 1 popping it in with a small
    overshoot: a solid disc for a `hub`, otherwise a ring with a dot inside."""
    if amount <= 0:
        return
    s = r * max(0.0, vb.ease_out_back(amount))
    if hub:
        demo.dot(cv, x, y, s, color=color)
        return
    demo.dot(cv, x, y, s, color=demo.BG)
    cv.arc(x, y, s, 0, 2 * math.pi, color, width=max(1.0, r * 0.18))
    demo.dot(cv, x, y, s * 0.32, color=demo.INK)


def draw_network(cv, nodes, edges, p, color=demo.TEAL, hub_color=demo.ACCENT, r=16, width=3, hubs=(0,), **kw):
    """Draw the network of `nodes` (a list of (x, y)) and `edges` (`(a, b)`
    index pairs, in build order) at progress `p` (0 -> 1). Lines go under the
    nodes and grow from `a` towards `b` with a bright tip; nodes listed in
    `hubs` are drawn larger and solid. `kw` goes to `network_timing`.
    Returns the bounding Box of the nodes shown so far."""
    shown, lines = network_timing(edges, p, **kw)
    for (a, b), f in zip(edges, lines):
        if f <= 0:
            continue
        (x0, y0), (x1, y1) = nodes[a], nodes[b]
        e = vb.ease_out_quint(f)
        x, y = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
        cv.line(x0, y0, x, y, color, width=width)
        if f < 1:
            demo.dot(cv, x, y, width * 1.3, color=demo.INK)
    for i, amount in shown.items():
        hub = i in hubs
        draw_node(cv, *nodes[i], r * (1.5 if hub else 1.0), hub_color if hub else color, amount, hub=hub)
    pts = [nodes[i] for i, a in shown.items() if a > 0]
    if not pts:
        return vb.Box(0, 0, 0, 0)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return vb.Box(min(xs) - r, min(ys) - r, max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r)


def _demo_graph():
    cx, cy = demo.W / 2, demo.H / 2
    rx, ry = demo.H * 0.5, demo.H * 0.34
    ring = [(cx + rx * math.cos(a), cy + ry * math.sin(a))
            for a in (math.radians(d) for d in (-90, -35, 15, 70, 125, 180, 230))]
    nodes = [(cx, cy)] + ring
    edges = [(0, 1), (0, 3), (0, 6), (0, 2), (0, 5), (0, 4), (0, 7), (1, 2), (3, 4), (5, 6), (7, 1)]
    return nodes, edges


def draw(n, cv):
    nodes, edges = _demo_graph()
    box = draw_network(cv, nodes, edges, demo.phase(n, 0.2, 2.6))
    cv.mark('network', *box)


CAPABILITY = Capability(
    id='connector-network',
    name='Connector network',
    family='shapes',
    group='Explainer & infographic',
    aliases=('node link animation', 'linked nodes', 'network diagram build'),
    definition='Dots pop onto the screen and straight lines grow between them one after another, '
               'until a web of connected points has been drawn.',
    phrasings=('build up a network diagram, one connection at a time',
               'dots that link together with lines as they appear',
               'animate the nodes and links of a graph drawing themselves'),
    related=('force-directed-network-settle', 'flowchart-build', 'org-chart-grow', 'chord-diagram-draw',
             'flow-map-lines', 'sankey-flow'),
    api=('videobuilder.capabilities.shapes.connector_network.draw_network',
         'videobuilder.capabilities.shapes.connector_network.network_timing',
         'videobuilder.capabilities.shapes.connector_network.draw_node'),
    demo=lambda: demo.film(draw),
)

"""Org chart grow: a hierarchy of labelled boxes builds down the screen one
rank at a time -- the top box appears, elbow connectors run down and out from
it, the next rank of boxes settles in where the lines land, and so on to the
bottom row."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PANEL = '#1d1f26'


def layout_org_chart(tree, x, y, w, h, box_w=120, box_h=44):
    """Place the boxes of `tree`, a `(label, [children])` nested tuple, inside
    the area (x, y, w, h). Leaves share the width evenly, each parent sits
    centred over its children, and ranks are spaced evenly top to bottom.
    Returns a list of nodes in depth-first order, each a dict with `label`,
    `x`, `y` (box centre), `depth`, `parent` (index, or None for the root),
    `w` and `h`."""
    nodes = []

    def walk(node, depth, parent):
        label, children = node
        i = len(nodes)
        nodes.append({'label': label, 'depth': depth, 'parent': parent, 'kids': []})
        for c in children:
            nodes[i]['kids'].append(walk(c, depth + 1, i))
        return i

    walk(tree, 0, None)
    leaves = [n for n in nodes if not n['kids']]
    ranks = max(n['depth'] for n in nodes) + 1
    for k, n in enumerate(leaves):
        n['x'] = x + w * (k + 0.5) / len(leaves)
    for n in sorted(nodes, key=lambda n: -n['depth']):
        if n['kids']:
            xs = [nodes[c]['x'] for c in n['kids']]
            n['x'] = (min(xs) + max(xs)) / 2
        n['y'] = y + box_h / 2 + (h - box_h) * (n['depth'] / (ranks - 1) if ranks > 1 else 0)
        n['w'], n['h'] = box_w, box_h
    for n in nodes:
        del n['kids']
    return nodes


def rank_progress(ranks, p, wire=0.45):
    """How far each rank of an org chart with `ranks` levels has built at
    progress `p` (0 -> 1): a list of `(lines, boxes)` 0 -> 1 pairs, one per
    rank. Each rank gets an equal slot; its connectors from the rank above
    draw over the first `wire` of the slot and its boxes come in over the
    rest. The root has no connectors, so its `lines` is always 1."""
    p = vb.clamp01(p)
    out = []
    for d in range(ranks):
        t = p * ranks - d
        if d == 0:
            out.append((1.0, vb.clamp01(t)))
        else:
            out.append((vb.clamp01(t / wire), vb.clamp01((t - wire * 0.8) / (1 - wire * 0.8))))
    return out


def _elbow(cv, parent, kids, amount, color, width):
    """The connector from `parent` down to its `kids`: a stem from the parent's
    bottom edge to a bus line, the bus spreading out both ways, then a drop
    into each child's top edge, drawn in that order over `amount` 0 -> 1."""
    px, top = parent['x'], parent['y'] + parent['h'] / 2
    bottom = min(k['y'] - k['h'] / 2 for k in kids)
    bus = (top + bottom) / 2
    stem = vb.clamp01(amount / 0.3)
    spread = vb.ease_out_quint(vb.clamp01((amount - 0.3) / 0.4))
    drop = vb.ease_out_quint(vb.clamp01((amount - 0.65) / 0.35))
    if stem > 0:
        cv.line(px, top, px, top + (bus - top) * stem, color, width=width)
    if spread > 0:
        left, right = min(k['x'] for k in kids), max(k['x'] for k in kids)
        cv.line(px - (px - left) * spread - width / 2, bus, px + (right - px) * spread + width / 2, bus,
                color, width=width)
    if drop > 0:
        for k in kids:
            end = k['y'] - k['h'] / 2
            cv.line(k['x'], bus, k['x'], bus + (end - bus) * drop, color, width=width)


def draw_org_box(cv, node, amount, fill=PANEL, edge=demo.TEAL, ink=demo.INK, font=None):
    """One labelled box of the chart, `amount` 0 -> 1 fading it in as it
    rises a few pixels and grows into place with a slight overshoot."""
    if amount <= 0:
        return
    s = 0.85 + 0.15 * vb.ease_out_back(amount)
    w, h = node['w'] * s, node['h'] * s
    cx, cy = node['x'], node['y'] + 10 * (1 - vb.ease_out_quint(amount))
    x, y = cx - w / 2, cy - h / 2
    with cv.layer(opacity=vb.clamp01(amount * 1.6)):
        cv.rect(x, y, w, h, fill, radius=8 * s)
        if edge:
            cv.outline(x, y, w, h, edge, width=2, radius=8 * s)
        f = font or demo.font(round(node['h'] * 0.36), 700)
        demo.word(cv, node['label'], cx, cy, font=f, color=ink)


def draw_org_chart(cv, nodes, p, line=demo.TEAL, width=2.5, root_fill=demo.ACCENT, root_ink=demo.BG, **kw):
    """Draw the chart laid out by `layout_org_chart` at progress `p` (0 -> 1):
    the root first, then each rank's connectors followed by its boxes (see
    `rank_progress`, which `kw` goes to). Connectors go under the boxes.
    Returns the bounding Box of the boxes shown so far."""
    ranks = max(n['depth'] for n in nodes) + 1
    prog = rank_progress(ranks, p, **kw)
    for i, n in enumerate(nodes):
        kids = [k for k in nodes if k['parent'] == i]
        if kids:
            _elbow(cv, n, kids, prog[n['depth'] + 1][0], line, width)
    shown = []
    for n in nodes:
        amount = prog[n['depth']][1]
        if n['parent'] is None:
            draw_org_box(cv, n, amount, fill=root_fill, edge=None, ink=root_ink)
        else:
            draw_org_box(cv, n, amount, edge=line)
        if amount > 0:
            shown.append(n)
    if not shown:
        return vb.Box(0, 0, 0, 0)
    x0 = min(n['x'] - n['w'] / 2 for n in shown)
    y0 = min(n['y'] - n['h'] / 2 for n in shown)
    x1 = max(n['x'] + n['w'] / 2 for n in shown)
    y1 = max(n['y'] + n['h'] / 2 for n in shown)
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


TREE = ('Director', [
    ('Design', [('Brand', []), ('Product', [])]),
    ('Engineering', [('Web', []), ('Mobile', [])]),
    ('Operations', [('Finance', []), ('People', [])]),
])


def draw(n, cv):
    nodes = layout_org_chart(TREE, 50, 70, demo.W - 100, demo.H - 140, box_w=118, box_h=42)
    box = draw_org_chart(cv, nodes, demo.phase(n, 0.2, 2.6))
    cv.mark('chart', *box)


CAPABILITY = Capability(
    id='org-chart-grow',
    name='Org chart grow',
    family='broadcast',
    group='Process diagrams',
    aliases=('hierarchy tree reveal', 'org tree build', 'organisation chart build'),
    definition='A chart of labelled boxes builds from the top down, connector lines branching out from '
               'each level before the boxes of the next level appear beneath them.',
    phrasings=('show our team structure building down from the boss, one row at a time',
               'animate an org chart where the lines branch out and the boxes pop in under them',
               'a reporting-line diagram that grows level by level'),
    related=('bar-grow', 'treemap-re-layout', 'stacked-bar-build', 'connector-network', 'recursive-tree',
             'waterfall-build'),
    api=('videobuilder.capabilities.broadcast.org_chart_grow.draw_org_chart',
         'videobuilder.capabilities.broadcast.org_chart_grow.layout_org_chart',
         'videobuilder.capabilities.broadcast.org_chart_grow.rank_progress',
         'videobuilder.capabilities.broadcast.org_chart_grow.draw_org_box'),
    demo=lambda: demo.film(draw),
)

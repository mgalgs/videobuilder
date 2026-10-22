"""Sankey flow: a chart of quantities moving between stages, each move drawn
as a curved band whose thickness is its share, the bands streaming out from
the left-hand nodes and pouring into the next column."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PALETTE = (demo.ACCENT, demo.TEAL, '#f2b84b', '#7f8cff', '#c77dff', '#5fb4ff', '#9bd36b')


def sankey_layout(columns, links, box, node_width=18, gap=22):
    """Place a Sankey chart in `box` (a `vb.Box` or (x, y, w, h)).

    `columns` is a list of columns, each a list of node names, left to right;
    `links` is (source, target, value) triples from one column to a later one.
    A node is as tall as the larger of what flows into and out of it, on one
    shared scale so the fullest column fills the box height; each column is
    centred vertically with `gap` px between nodes.

    Returns `(nodes, bands)`: `nodes` maps name -> dict(x, y, w, h, column,
    value), and `bands` is one dict per link, in order, with the source/target
    names, `value`, and the band's edges `x0, y0, x1, y1, thick` (y0/y1 the
    band's top at the source and target)."""
    bx, by, bw, bh = tuple(box)
    col_of = {name: i for i, col in enumerate(columns) for name in col}
    for s, t, _ in links:
        if s not in col_of or t not in col_of:
            raise ValueError(f'sankey link {s!r} -> {t!r} names a node not in any column')
        if col_of[t] <= col_of[s]:
            raise ValueError(f'sankey link {s!r} -> {t!r} must run left to right')
    out_sum = {n: 0.0 for n in col_of}
    in_sum = {n: 0.0 for n in col_of}
    for s, t, v in links:
        out_sum[s] += v
        in_sum[t] += v
    value = {n: max(out_sum[n], in_sum[n]) for n in col_of}
    scale = min((bh - gap * (len(col) - 1)) / max(sum(value[n] for n in col), 1e-9) for col in columns)
    step = (bw - node_width) / max(len(columns) - 1, 1)
    nodes = {}
    for i, col in enumerate(columns):
        total = sum(value[n] for n in col) * scale + gap * (len(col) - 1)
        y = by + (bh - total) / 2
        for n in col:
            h = value[n] * scale
            nodes[n] = dict(x=bx + i * step, y=y, w=node_width, h=h, column=i, value=value[n])
            y += h + gap
    order = {n: k for col in columns for k, n in enumerate(col)}
    out_y = {n: nodes[n]['y'] for n in nodes}
    in_y = {n: nodes[n]['y'] for n in nodes}
    top0, top1 = {}, {}
    # stack bands at each node in the order of the node at their other end, so they don't cross needlessly
    for k in sorted(range(len(links)), key=lambda k: (col_of[links[k][1]], order[links[k][1]])):
        s = links[k][0]
        top0[k] = out_y[s]
        out_y[s] += links[k][2] * scale
    for k in sorted(range(len(links)), key=lambda k: (col_of[links[k][0]], order[links[k][0]])):
        t = links[k][1]
        top1[k] = in_y[t]
        in_y[t] += links[k][2] * scale
    bands = []
    for k, (s, t, v) in enumerate(links):
        bands.append(dict(source=s, target=t, value=v, thick=v * scale,
                          x0=nodes[s]['x'] + node_width, y0=top0[k], x1=nodes[t]['x'], y1=top1[k]))
    return nodes, bands


def _band_path(ctx, b):
    x0, x1, t = b['x0'], b['x1'], b['thick']
    mx = (x0 + x1) / 2
    ctx.move_to(x0, b['y0'])
    ctx.curve_to(mx, b['y0'], mx, b['y1'], x1, b['y1'])
    ctx.line_to(x1, b['y1'] + t)
    ctx.curve_to(mx, b['y1'] + t, mx, b['y0'] + t, x0, b['y0'] + t)
    ctx.close_path()


def sankey_flow(cv, columns, links, progress, box=None, colors=None, node_width=18, gap=22,
                band_alpha=0.55, labels=True, font=None, label_color=demo.INK, value_format='{:g}'):
    """Draw a Sankey chart at `progress` 0 -> 1: the bands stream left to
    right, a sweeping front carrying them out of each node and into the next
    column, and each node grows to full height as the front reaches it.

    `columns` and `links` are as in `sankey_layout`; `box` defaults to the
    frame with room for labels at either side. `colors` maps node name ->
    colour (default: a palette in node order); a band shades from its
    source's colour to its target's. `labels` writes each node's name and
    value beside it (left of the first column, right of the others), fading
    in as the node arrives. Call it every frame with an eased progress, e.g.
    `sankey_flow(cv, cols, links, vb.ease_in_out_quart(p))`. Returns the
    layout's `(nodes, bands)`."""
    if box is None:
        box = vb.Box(150, 60, cv.width - 300, cv.height - 120)
    nodes, bands = sankey_layout(columns, links, box, node_width, gap)
    names = [n for col in columns for n in col]
    colors = dict(colors or {})
    for i, n in enumerate(names):
        colors.setdefault(n, PALETTE[i % len(PALETTE)])
    p = vb.clamp01(progress)
    left = min(nd['x'] for nd in nodes.values())
    right = max(nd['x'] + nd['w'] for nd in nodes.values())
    front = left + (right - left + 40) * p   # a little past the last column, so it lands fully
    ctx = cv.ctx

    def arrived(nd):  # 0 -> 1 as the front crosses the node
        return vb.clamp01((front - nd['x']) / (nd['w'] + 30))

    # bands under the nodes, clipped at the front, with a soft feathered lip
    feather = 36
    for b in bands:
        if front <= b['x0']:
            continue
        ctx.save()
        ctx.rectangle(b['x0'] - 1, 0, max(0.0, front - b['x0']) + 1, cv.height)
        ctx.clip()
        _band_path(ctx, b)
        grad = cairo.LinearGradient(b['x0'], 0, b['x1'], 0)
        grad.add_color_stop_rgba(0, *vb.rgba(colors[b['source']], band_alpha))
        grad.add_color_stop_rgba(1, *vb.rgba(colors[b['target']], band_alpha))
        ctx.set_source(grad)
        ctx.fill_preserve()
        if front < b['x1']:  # brighten the leading edge so the flow reads as moving
            lip = cairo.LinearGradient(front - feather, 0, front, 0)
            lip.add_color_stop_rgba(0, 1, 1, 1, 0)
            lip.add_color_stop_rgba(1, 1, 1, 1, 0.35)
            ctx.set_source(lip)
            ctx.fill()
        else:
            ctx.new_path()
        ctx.restore()
    f = font or demo.font(18, 700)
    small = demo.mono(14)
    for n in names:
        nd = nodes[n]
        a = arrived(nd)
        if a <= 0:
            continue
        h = nd['h'] * vb.ease_out_expo(a)
        cy = nd['y'] + nd['h'] / 2
        cv.rect(nd['x'], cy - h / 2, nd['w'], h, colors[n], radius=3)
        cv.mark(f'node:{n}', nd['x'], nd['y'], nd['w'], nd['h'])
        if not labels:
            continue
        lines = [n]
        tw, th = vb.text.block_size(lines, f)
        vw, vh = vb.text.block_size([value_format.format(nd['value'])], small)
        first = nd['column'] == 0
        x = nd['x'] - 12 - max(tw, vw) if first else nd['x'] + nd['w'] + 12
        top = cy - (th + vh) / 2
        vb.text.draw(cv, lines, f, x, top, label_color, align='right' if first else 'left',
                     width=max(tw, vw), alpha=a)
        vb.text.draw(cv, [value_format.format(nd['value'])], small, x, top + th, demo.MUTED,
                     align='right' if first else 'left', width=max(tw, vw), alpha=a)
    return nodes, bands


COLUMNS = (('Search', 'Social', 'Email'), ('Signed up', 'Left'), ('Paid', 'Free'))
LINKS = (('Search', 'Signed up', 40), ('Search', 'Left', 22), ('Social', 'Signed up', 16),
         ('Social', 'Left', 26), ('Email', 'Signed up', 22), ('Email', 'Left', 6),
         ('Signed up', 'Paid', 30), ('Signed up', 'Free', 48))
COLORS = {'Search': demo.ACCENT, 'Social': '#f2b84b', 'Email': demo.TEAL, 'Signed up': '#7f8cff',
          'Left': '#5b5f6b', 'Paid': '#9bd36b', 'Free': '#c77dff'}


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.25, 2.45))
    sankey_flow(cv, COLUMNS, LINKS, p, box=vb.Box(150, 56, demo.W - 300, demo.H - 112), colors=COLORS)


CAPABILITY = Capability(
    id='sankey-flow',
    name='Sankey flow',
    family='broadcast',
    group='Charts',
    aliases=('sankey diagram', 'alluvial diagram', 'flow diagram'),
    definition='A chart whose curved bands stream from one column of categories into the next, '
               'each band as thick as the amount it carries, so you see where everything ends up.',
    phrasings=('show how the users split up between stages as flowing bands',
               'a flow chart where the thickness of each stream shows how much goes where',
               'animate the money pouring from sources into where it gets spent'),
    related=('streamlines', 'flowchart-build', 'flow-map-lines', 'flow-field', 'connector-network',
             'decision-tree-branch-growth'),
    api=('videobuilder.capabilities.broadcast.sankey_flow.sankey_flow',
         'videobuilder.capabilities.broadcast.sankey_flow.sankey_layout'),
    demo=lambda: demo.film(draw),
)

"""Hub-and-spoke spread: a central node pops in, then a ring of satellite
nodes bursts out of it, each travelling along its own spoke to a place on a
circle around the hub while the spoke line stretches behind it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def spoke_positions(cx, cy, count, rx, ry=None, start=-90.0):
    """`count` points spaced evenly around an ellipse of radii (`rx`, `ry`)
    centred on (cx, cy), the first at `start` degrees (-90 is straight up),
    going clockwise. Returns a list of (x, y)."""
    ry = rx if ry is None else ry
    out = []
    for i in range(count):
        a = math.radians(start + 360.0 * i / max(count, 1))
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def spread_timing(count, p, hub=0.22, stagger=0.5):
    """The build state at progress `p` (0 -> 1) of a hub with `count` spokes.
    Returns `(hub_amount, spokes)`: the hub's own 0 -> 1 pop-in over the first
    `hub` of the run, then one 0 -> 1 travel progress per spoke. The spokes
    start one after another across `stagger` of the remaining time (0 sends
    them all out together) and each takes the rest to arrive."""
    p = vb.clamp01(p)
    hub_amount = vb.clamp01(p / hub) if hub > 0 else 1.0
    rest = 1 - hub
    step = rest * stagger / max(count - 1, 1)
    length = rest - step * (count - 1)
    spokes = [vb.clamp01((p - hub - i * step) / length) for i in range(count)]
    return hub_amount, spokes


def draw_hub_and_spoke(cv, cx, cy, targets, p, labels=(), hub_label='', hub_r=78, node_r=46,
                       hub_color=demo.ACCENT, node_color=demo.TEAL, line=demo.MUTED, width=4, **kw):
    """Draw a hub at (cx, cy) spreading satellites out to `targets` (a list of
    (x, y), e.g. from `spoke_positions`) at progress `p` (0 -> 1). Each
    satellite leaves the hub centre, overshoots slightly and settles on its
    target, growing as it goes; its spoke is drawn from the hub to wherever it
    is now. `labels` (one per target) and `hub_label` are written inside the
    discs once they are mostly out. `kw` goes to `spread_timing`. Returns the
    bounding Box of what is shown."""
    hub_amount, spokes = spread_timing(len(targets), p, **kw)
    placed = []
    for (tx, ty), f in zip(targets, spokes):
        e = vb.ease_out_back(f) if f > 0 else 0.0
        placed.append((cx + (tx - cx) * e, cy + (ty - cy) * e, f))
    for x, y, f in placed:
        if f > 0:
            cv.line(cx, cy, x, y, line, width=width, alpha=min(1.0, f * 3))
    for i, (x, y, f) in enumerate(placed):
        if f <= 0:
            continue
        r = node_r * (0.35 + 0.65 * vb.ease_out_quint(f))
        demo.dot(cv, x, y, r, color=node_color)
        if i < len(labels) and f > 0.55:
            demo.word(cv, labels[i], x, y, size=round(node_r * 0.62), color=demo.BG,
                      alpha=vb.clamp01((f - 0.55) / 0.3))
    if hub_amount > 0:
        s = hub_r * max(0.0, vb.ease_out_back(hub_amount))
        demo.dot(cv, cx, cy, s * 1.22, color=hub_color, alpha=0.25)
        demo.dot(cv, cx, cy, s, color=hub_color)
        if hub_label and hub_amount > 0.6:
            demo.word(cv, hub_label, cx, cy, size=round(hub_r * 0.42), color=demo.INK,
                      alpha=vb.clamp01((hub_amount - 0.6) / 0.4))
    pts = [(cx, cy, hub_r)] + [(x, y, node_r) for x, y, f in placed if f > 0]
    x0 = min(x - r for x, _, r in pts)
    y0 = min(y - r for _, y, r in pts)
    x1 = max(x + r for x, _, r in pts)
    y1 = max(y + r for _, y, r in pts)
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


LABELS = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    targets = spoke_positions(cx, cy, len(LABELS), demo.H * 0.62, demo.H * 0.36)
    box = draw_hub_and_spoke(cv, cx, cy, targets, demo.phase(n, 0.2, 2.4), labels=LABELS, hub_label='HUB')
    cv.mark('hub', *box)


TECHNIQUE = Technique(
    id='hub-and-spoke-spread',
    name='Hub-and-spoke spread',
    family='broadcast',
    group='Process diagrams',
    aliases=('hub and spoke diagram', 'radial spread', 'star diagram', 'central node fan out'),
    definition='A central circle appears and a ring of smaller circles shoots out of it in turn, '
               'each trailing a line back to the middle, until they sit evenly around it.',
    phrasings=('show one main idea with all its parts flying out around it',
               'a center bubble that spreads out into connected bubbles',
               'animate a radial diagram where the items burst out from the middle'),
    related=('radar-chart-fill', 'force-directed-network-settle', 'connector-network', 'circle-packing',
             'avatar-stack-spread', 'sunburst-build'),
    api=('videobuilder.techniques.broadcast.hub_and_spoke_spread.draw_hub_and_spoke',
         'videobuilder.techniques.broadcast.hub_and_spoke_spread.spoke_positions',
         'videobuilder.techniques.broadcast.hub_and_spoke_spread.spread_timing'),
    demo=lambda: demo.film(draw),
)

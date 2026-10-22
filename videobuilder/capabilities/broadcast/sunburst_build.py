"""Sunburst build: a hierarchy drawn as concentric rings of arc segments --
the root category ring nearest the centre, each child ring split under its
parent's arc -- assembles from the middle outward, every segment sweeping
round from its start angle while its ring thickens into place."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba


def tint(color, k):
    """`color` mixed toward white by `k` (0 keeps it, 1 is white), as an (r, g, b) tuple."""
    r, g, b, _ = rgba(color)
    return tuple(round(255 * (c + (1 - c) * k)) for c in (r, g, b))


def sunburst_layout(tree, a0=-math.pi / 2, a1=1.5 * math.pi, depth=0, color=None, fade=0.28):
    """Flatten `tree` -- a list of `(value, color_or_None, children)` nodes --
    into segments `(depth, start, end, color)`, each node's angle in
    proportion to its value within its parent's span `a0..a1` (radians,
    clockwise from +x, as `Canvas.arc`). A node with no colour of its own
    inherits its parent's, lightened by `fade` per ring. Parents come before
    their children."""
    total = sum(v for v, _, _ in tree) or 1
    out, a = [], a0
    for value, own, children in tree:
        b = a + (a1 - a0) * value / total
        c = own if own is not None else tint(color, fade)
        out.append((depth, a, b, c))
        if children:
            out += sunburst_layout(children, a, b, depth + 1, c, fade)
        a = b
    return out


def sunburst_build(cv, cx, cy, segments, p, r0=60.0, ring=60.0, gap=4.0, stagger=0.55, ease=vb.ease_out_quint,
                   alpha=1.0):
    """Draw `segments` (from `sunburst_layout`) as a sunburst at progress `p`
    (0 -> 1), centred at (cx, cy): ring `d` spans radii `r0 + d * ring` to
    `r0 + (d + 1) * ring`, less `gap` pixels between rings and segments.
    Rings start one after another from the centre, their starts spread
    across the first `stagger` of the run; within its ring each segment
    sweeps clockwise from its start angle while the ring grows outward from
    its inner edge. Returns each segment's progress, in order."""
    depths = max((s[0] for s in segments), default=0)
    out = []
    for d, a, b, color in segments:
        start = stagger * d / max(1, depths)
        q = ease(vb.clamp01((p - start) / (1 - stagger))) if stagger < 1 else float(p >= start)
        out.append(q)
        if q <= 0:
            continue
        inner = r0 + d * ring + gap / 2
        thick = (ring - gap) * (0.35 + 0.65 * q)
        mid = inner + thick / 2
        pad = min((b - a) / 3, gap / 2 / mid)
        end = a + pad + (b - a - 2 * pad) * q
        if end > a + pad:
            cv.arc(cx, cy, mid, a + pad, end, color, width=thick, alpha=alpha)
    return out


AMBER, BLUE = '#f2b84b', '#6c8cff'
TREE = [
    (34, demo.ACCENT, [(14, None, [(8, None, []), (6, None, [])]), (12, None, [(12, None, [])]),
                       (8, None, [])]),
    (26, demo.TEAL, [(16, None, [(9, None, []), (4, None, []), (3, None, [])]), (10, None, [])]),
    (24, AMBER, [(10, None, [(10, None, [])]), (8, None, [(5, None, []), (3, None, [])]), (6, None, [])]),
    (16, BLUE, [(9, None, [(6, None, []), (3, None, [])]), (7, None, [])]),
]
SEGMENTS = sunburst_layout(TREE)


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    sunburst_build(cv, cx, cy, SEGMENTS, demo.phase(n, 0.2, 2.3), r0=70, ring=62, gap=5, stagger=0.5)
    k = demo.phase(n, 0.0, 0.5)
    demo.word(cv, '100%', cx, cy - 6, size=34, alpha=k)
    demo.word(cv, 'TOTAL', cx, cy + 22, size=13, color=demo.MUTED, weight=700, alpha=k)
    cv.mark('chart', cx - 256, cy - 256, 512, 512)


TECHNIQUE = Technique(
    id='sunburst-build',
    name='Sunburst build',
    family='broadcast',
    group='Charts',
    aliases=('sunburst chart reveal', 'radial treemap build', 'multi-level pie build', 'ring chart build'),
    definition='A layered ring chart grows outward from its centre, each ring of arc segments sweeping '
               'round in turn so the sub-categories fan out beneath the category that holds them.',
    phrasings=('animate a sunburst chart so the inner ring draws first and the outer rings spread out after it',
               'a nested donut chart where each level of the breakdown sweeps in around the one inside it',
               'build up a hierarchy as rings around a centre total, layer by layer'),
    related=('synthwave-sun', 'diffraction-spikes', 'hub-and-spoke-spread', 'circle-packing', 'org-chart-grow',
             'phyllotaxis'),
    api=('videobuilder.techniques.broadcast.sunburst_build.sunburst_build',
         'videobuilder.techniques.broadcast.sunburst_build.sunburst_layout',
         'videobuilder.techniques.broadcast.sunburst_build.tint'),
    demo=lambda: demo.film(draw),
)

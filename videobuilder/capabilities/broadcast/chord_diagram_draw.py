"""Chord Diagram Draw: the category arcs sweep in around a circle first, then
curved ribbons grow across the middle from one arc to another, each as wide
at its ends as the flow it carries."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

TOP = -math.pi / 2  # canvas angles run clockwise from 3 o'clock


def chord_layout(matrix, gap=0.06, start=TOP):
    """Angles for a chord diagram of the square flow `matrix` (`matrix[i][j]`:
    how much goes from category i to j). Returns `(groups, spans)`: `groups[i]`
    is the `(a0, a1)` arc of category i, sized by its row total with `gap`
    radians between neighbours, clockwise from `start`; `spans[i][j]` is the
    slice of arc i that the i -> j flow leaves from."""
    n = len(matrix)
    total = sum(sum(row) for row in matrix) or 1
    k = (2 * math.pi - gap * n) / total
    groups, spans, a = [], [], start
    for row in matrix:
        g0, sub = a, []
        for v in row:
            sub.append((a, a + v * k))
            a += v * k
        groups.append((g0, a))
        spans.append(sub)
        a += gap
    return groups, spans


def _quad(p0, c, p1, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1])


def _on(cx, cy, r, a):
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def ribbon_points(cx, cy, r, src, dst, grow=1.0, steps=40):
    """The outline of one ribbon from the arc slice `src` = (a0, a1) to `dst`,
    its two edges bowing through the centre, as a closed point list.
    `grow` (0 -> 1) is how far it has reached from `src` toward `dst`; short
    of 1 the tip is cut square across the two edges."""
    grow = vb.clamp01(grow)
    if grow <= 0:
        return []
    (s0, s1), (d0, d1), c = src, dst, (cx, cy)
    n = max(2, round(steps * grow))
    ts = [grow * i / n for i in range(n + 1)]
    left = [_quad(_on(cx, cy, r, s1), c, _on(cx, cy, r, d0), t) for t in ts]   # s1 -> d0
    right = [_quad(_on(cx, cy, r, s0), c, _on(cx, cy, r, d1), t) for t in ts]  # s0 -> d1
    pts = left
    if grow >= 1:
        m = max(2, round(steps * abs(d1 - d0) / math.pi))
        pts = pts + [_on(cx, cy, r, d0 + (d1 - d0) * i / m) for i in range(1, m)]
    pts = pts + right[::-1]
    m = max(2, round(steps * abs(s1 - s0) / math.pi))
    return pts + [_on(cx, cy, r, s0 + (s1 - s0) * i / m) for i in range(1, m)]


def draw_chord_diagram(cv, cx, cy, r, matrix, colors, arcs=1.0, ribbons=1.0, width=14, gap=0.06,
                       stagger=0.5, ribbon_alpha=0.55, start=TOP):
    """A chord diagram of `matrix` centred at (cx, cy), the category arcs
    `width` px thick just outside radius `r`, ribbons inside it. `colors[i]`
    colours category i and the ribbons leaving it. `arcs` (0 -> 1) sweeps the
    arcs on, each clockwise from its start, the later ones a little behind
    (`stagger` of the run is spread across them); `ribbons` (0 -> 1) grows
    the ribbons in the same staggered way, the pair i, j drawn once from the
    lower index. Returns the `groups` from `chord_layout`."""
    groups, spans = chord_layout(matrix, gap, start)
    n = len(groups)

    def local(p, i, count):
        lag = stagger * i / max(1, count - 1)
        return vb.clamp01((p - lag) / (1 - stagger)) if stagger < 1 else float(p >= lag)

    pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if matrix[i][j] or matrix[j][i]]
    for k, (i, j) in enumerate(pairs):
        g = vb.ease_in_out_quart(local(ribbons, k, len(pairs)))
        pts = ribbon_points(cx, cy, r - 2, spans[i][j], spans[j][i], g)
        vb.paths.draw(cv, pts, colors[i % len(colors)], fill=True, alpha=ribbon_alpha)
    for i, (a0, a1) in enumerate(groups):
        p = vb.ease_out_quint(local(arcs, i, n))
        if p > 0:
            cv.arc(cx, cy, r + width / 2, a0, a0 + (a1 - a0) * p, colors[i % len(colors)], width=width)
    return groups


FLOWS = [
    [0, 14, 6, 9, 3, 8],
    [11, 0, 7, 4, 10, 2],
    [5, 9, 0, 12, 3, 6],
    [8, 3, 10, 0, 7, 4],
    [2, 12, 4, 6, 0, 9],
    [7, 3, 8, 5, 11, 0],
]
COLORS = (demo.ACCENT, demo.TEAL, '#f2b84b', '#7f8cff', '#c77dff', '#5ab0f0')
LABELS = ('North', 'East', 'South', 'West', 'Coast', 'Inland')


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2, 200
    arcs = demo.phase(n, 0.2, 1.2)
    groups = draw_chord_diagram(cv, cx, cy, r, FLOWS, COLORS, arcs=arcs, ribbons=demo.phase(n, 1.1, 2.6))
    f = demo.font(18, 700)
    for i, (a0, a1) in enumerate(groups):
        a = (a0 + a1) / 2
        x, y = _on(cx, cy, r + 48, a)
        alpha = vb.clamp01(arcs * len(groups) - i)
        demo.word(cv, LABELS[i], x, y, size=18, color=COLORS[i], font=f, alpha=alpha)
    cv.mark('chord', cx - r - 14, cy - r - 14, 2 * r + 28, 2 * r + 28)


CAPABILITY = Capability(
    id='chord-diagram-draw',
    name='Chord diagram draw',
    family='broadcast',
    group='Charts',
    aliases=('chord transition', 'circular flow chart', 'chord chart', 'ribbon diagram'),
    definition='Coloured arcs sweep on around a ring, then curved bands grow through the middle linking '
               'pairs of arcs, each band as thick as the amount flowing between them.',
    phrasings=('a circle of categories with ribbons drawing in between them to show who sends what to whom',
               'animate a chord chart: the outer ring first, then the connecting bands',
               'flows between groups shown as curved bands across a circle, growing in one by one'),
    related=('cycle-diagram-rotation', 'flowchart-build', 'progress-ring', 'decision-tree-branch-growth',
             'spiral-expansion-draw', 'connector-network'),
    api=('videobuilder.capabilities.broadcast.chord_diagram_draw.draw_chord_diagram',
         'videobuilder.capabilities.broadcast.chord_diagram_draw.chord_layout',
         'videobuilder.capabilities.broadcast.chord_diagram_draw.ribbon_points'),
    demo=lambda: demo.film(draw),
)

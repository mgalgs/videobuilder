"""Decision tree branch growth: a tree diagram builds itself from the root,
each branch line drawing outward and the node at its tip popping in as the
line arrives, one level after another."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tree_layout(tree, x, y, w, level_gap):
    """Place a tree inside the band starting at (x, y), `w` wide, levels
    `level_gap` apart. `tree` is `(label, children)` or
    `(label, children, branch_label)`, children being the same shape. Each
    node gets horizontal room in proportion to its leaf count. Returns a
    list of `(depth, label, branch_label, (cx, cy), parent_index)`, parents
    before children; the root's parent index is None."""
    def leaves(t):
        kids = t[1]
        return sum(leaves(k) for k in kids) if kids else 1

    out = []

    def place(t, depth, left, width, parent):
        label, kids = t[0], t[1]
        branch = t[2] if len(t) > 2 else ''
        i = len(out)
        out.append((depth, label, branch, (left + width / 2, y + depth * level_gap), parent))
        total = sum(leaves(k) for k in kids)
        at = left
        for k in kids:
            share = width * leaves(k) / total
            place(k, depth + 1, at, share, i)
            at += share

    place(tree, 0, x, w, None)
    return out


def decision_tree_growth(cv, tree, p, box=None, node_w=170, node_h=50, level_gap=150,
                         line=demo.TEAL, root_color='#f2b43c', node_color='#1d2029',
                         ink=demo.INK, edge_ink=demo.MUTED, grow=0.6):
    """Draw `tree` (see `tree_layout`) grown to progress `p` (0 -> 1).

    The root fades and scales in first; then each depth gets an equal slot in
    which its branches draw from the parent's bottom edge to the child's top
    edge (eased out) over the first `grow` of the slot, and the child node
    pops in over the rest. `box` is `(x, y, w)`, the band the tree fills
    (default: the frame with margins). In a film, drive `p` from a clip's
    own frame count, e.g. `decision_tree_growth(cv, my_tree, f / frames)`."""
    x, y, w = box or (40, 60, cv.width - 80)
    nodes = tree_layout(tree, x, y + node_h / 2, w, level_gap)
    depth = max(n[0] for n in nodes)
    slot = 1 / (depth + 1)
    f_label = demo.font(round(node_h * 0.4), 800)
    f_edge = demo.font(round(node_h * 0.3), 600)

    def node_phase(d):
        if d == 0:
            return vb.clamp01(p / slot)
        start = d * slot
        return vb.clamp01((p - start - slot * grow) / (slot * (1 - grow)))

    # branches under the nodes
    for d, _, branch, (cx, cy), parent in nodes:
        if parent is None:
            continue
        q = vb.ease_out_quint(vb.clamp01((p - d * slot) / (slot * grow)))
        if q <= 0:
            continue
        px, py = nodes[parent][3]
        x0, y0 = px, py + node_h / 2
        x1, y1 = cx, cy - node_h / 2
        xe, ye = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
        cv.line(x0, y0, xe, ye, line, width=3)
        if branch:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            side = -1 if x1 < x0 else 1
            demo.word(cv, branch, mx + side * node_h * 0.45, my - node_h * 0.12, size=16, color=edge_ink, font=f_edge,
                      alpha=vb.clamp01(q * 2 - 1))
    for d, label, _, (cx, cy), _ in nodes:
        a = node_phase(d)
        if a <= 0:
            continue
        s = 0.7 + 0.3 * vb.ease_out_back(a)
        nw, nh = node_w * s, node_h * s
        nx, ny = cx - nw / 2, cy - nh / 2
        with cv.layer(opacity=min(1.0, a * 1.6)):
            if d == 0:
                cv.rect(nx, ny, nw, nh, root_color, radius=node_h * 0.16 * s)
                demo.word(cv, label, cx, cy, size=20, color=demo.BG, font=f_label)
            else:
                cv.rect(nx, ny, nw, nh, node_color, radius=node_h * 0.16 * s)
                cv.outline(nx, ny, nw, nh, line, width=2, radius=node_h * 0.16 * s)
                demo.word(cv, label, cx, cy, size=20, color=ink, font=f_label)


DEMO_TREE = ('Ship it today?', [
    ('Tests pass?', [('Deploy', [], 'yes'), ('Fix first', [], 'no')], 'yes'),
    ('Big change?', [('Plan review', [], 'yes'), ('Next sprint', [], 'no')], 'no'),
])


def _draw(n, cv):
    decision_tree_growth(cv, DEMO_TREE, demo.phase(n, 0.2, 2.6), box=(50, 95, demo.W - 100))


TECHNIQUE = Technique(
    id='decision-tree-branch-growth',
    name='Decision tree branch growth',
    family='broadcast',
    group='Process diagrams',
    aliases=('tree growth', 'branching diagram', 'decision tree reveal'),
    definition='A flowchart-style tree builds downward from its top question, each connecting '
               'line drawing out to the next level and the answer box popping in where it ends.',
    phrasings=('grow the decision tree out from the first question',
               'have the yes/no branches draw in one level at a time',
               'animate a branching flowchart building itself from the top'),
    related=('recursive-tree', 'chord-diagram-draw', 'treemap-re-layout', 'bar-grow',
             'differential-growth', 'sankey-flow'),
    api=('videobuilder.techniques.broadcast.decision_tree_branch_growth.decision_tree_growth',
         'videobuilder.techniques.broadcast.decision_tree_branch_growth.tree_layout'),
    demo=lambda: demo.film(_draw),
)

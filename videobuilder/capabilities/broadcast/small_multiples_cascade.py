"""Small multiples cascade: a grid of small, identical charts -- one per
category, all drawn against the same axis -- arrives panel by panel in
reading order, each panel landing and then its data growing in, so the
viewer can compare categories at a glance once the grid is full."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..ui.staggered_cascade_reveal import cascade, reveal


def mini_bars(cv, x, y, w, h, values, vmax, q, color=demo.TEAL, track=demo.LINE):
    """A tiny column chart filling the box (x, y, w, h): one column per value,
    every column measured against the shared `vmax` so panels compare, grown
    to progress `q` (0 -> 1, columns rising left to right). A baseline and a
    faint top line mark the shared scale."""
    cv.line(x, y, x + w, y, track, width=1)
    cv.line(x, y + h, x + w, y + h, demo.MUTED, width=1.5)
    n = len(values)
    slot = w / n
    bw = slot * 0.62
    grow = cascade(q, n, spread=0.5, ease=vb.ease_out_expo)
    for i, (v, g) in enumerate(zip(values, grow)):
        bh = h * min(v, vmax) / vmax * g
        if bh > 0.5:
            cv.rect(x + i * slot + (slot - bw) / 2, y + h - bh, bw, bh, color, radius=min(3, bw / 2))


def small_multiples(cv, panels, p, x, y, cols, cell_w, cell_h, gap=16, spread=0.6, draw_panel=None):
    """Draw a small-multiples grid at overall progress `p` (0 -> 1). `panels`
    is a list of per-panel data, laid out `cols` across from (x, y) in cells
    of `cell_w` x `cell_h` with `gap` between. Panels cascade in reading order
    (see `staggered_cascade_reveal.cascade`): each rises and fades in over its
    own slot, and `draw_panel(cv, panel, box, q)` draws its contents with that
    progress `q`, so the chart inside can build as the panel lands. Returns
    each panel's progress."""
    qs = cascade(p, len(panels), spread=spread, ease=vb.ease_out_quint)
    draw_panel = draw_panel or _plain_panel
    for i, (panel, q) in enumerate(zip(panels, qs)):
        r, c = divmod(i, cols)
        box = vb.Box(x + c * (cell_w + gap), y + r * (cell_h + gap), cell_w, cell_h)
        reveal(cv, lambda cv, panel=panel, box=box, q=q: draw_panel(cv, panel, box, q), q, rise=24)
    return qs


def _plain_panel(cv, panel, box, q):
    cv.rect(box.x, box.y, box.w, box.h, '#1c1e24', radius=10)
    mini_bars(cv, box.x + 14, box.y + 14, box.w - 28, box.h - 28, panel, max(panel), q)


REGIONS = (('North', (32, 41, 38, 52, 60, 66)),
           ('South', (28, 30, 35, 33, 40, 44)),
           ('East', (45, 50, 48, 61, 70, 78)),
           ('West', (20, 26, 31, 29, 34, 38)),
           ('Central', (38, 36, 44, 47, 50, 55)),
           ('Coast', (50, 58, 67, 74, 83, 95)),
           ('Hills', (18, 22, 20, 27, 25, 30)),
           ('Valley', (34, 39, 42, 40, 48, 51)))
VMAX = 100
HIGHLIGHT = 'Coast'
COLS, CW, CH, GAP = 4, 196, 156, 18


def _panel(cv, panel, box, q):
    name, values = panel
    color = demo.ACCENT if name == HIGHLIGHT else demo.TEAL
    cv.rect(box.x, box.y, box.w, box.h, '#1c1e24', radius=12)
    cv.outline(box.x, box.y, box.w, box.h, demo.LINE, width=1.5, radius=12)
    f = demo.font(17, 800)
    vb.text.draw(cv, [name], f, box.x + 14, box.y + 12, demo.INK)
    v = round(values[-1] * vb.clamp01(q))
    fv = demo.mono(16, 700)
    tw, _ = vb.text.block_size([str(v)], fv)
    vb.text.draw(cv, [str(v)], fv, box.x + box.w - 14 - tw, box.y + 13, color)
    mini_bars(cv, box.x + 14, box.y + 46, box.w - 28, box.h - 62, values, VMAX, vb.clamp01(q * 1.25 - 0.2),
              color=color)


def draw(n, cv):
    gw = COLS * CW + (COLS - 1) * GAP
    rows = -(-len(REGIONS) // COLS)
    gh = rows * CH + (rows - 1) * GAP
    x0, y0 = (demo.W - gw) / 2, (demo.H - gh) / 2 + 26
    demo.word(cv, 'Monthly sales by region', demo.W / 2, y0 - 38, size=28, color=demo.MUTED, weight=700)
    small_multiples(cv, REGIONS, demo.phase(n, 0.2, 2.5), x0, y0, COLS, CW, CH, GAP, spread=0.7,
                    draw_panel=_panel)
    cv.mark('grid', x0, y0, gw, gh)


CAPABILITY = Capability(
    id='small-multiples-cascade',
    name='Small multiples cascade',
    family='broadcast',
    group='Charts',
    aliases=('trellis cascade', 'panel grid reveal', 'small multiples build', 'faceted chart reveal'),
    definition='A grid of matching little charts, one per category and all on the same scale, fills in '
               'panel by panel, each chart building its data as its panel lands.',
    phrasings=('show a mini chart for every region in a grid and bring them in one after another',
               'lay out the same small graph for each category side by side and reveal them in sequence',
               'a wall of tiny bar charts on a shared axis that pops in tile by tile'),
    related=('staggered-cascade-reveal', 'springs-network', 'swiss-grid-slide', 'mograph-grid-flip',
             'dropdown-stagger-reveal', 'org-chart-grow'),
    api=('videobuilder.capabilities.broadcast.small_multiples_cascade.small_multiples',
         'videobuilder.capabilities.broadcast.small_multiples_cascade.mini_bars',
         'videobuilder.capabilities.ui.staggered_cascade_reveal.cascade'),
    demo=lambda: demo.film(draw),
)

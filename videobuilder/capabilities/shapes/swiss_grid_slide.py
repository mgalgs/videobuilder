"""Swiss Grid Slide: a modular grid draws itself in, a heavy rule wipes
across it, then column panels slide up into their cells one after another and
a letter drops onto the rule above each, everything snapping to the grid."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def column_progress(p, i, n, start=0.3, stagger=0.45):
    """Progress 0 -> 1 of column `i` of `n` at overall progress `p`: columns
    begin from `start`, each later one `stagger` of the remaining span spread
    across them, and all finish by 1."""
    span = 1 - start
    each = span * (1 - stagger)
    t0 = start + (span - each) * (i / max(1, n - 1))
    return vb.clamp01((p - t0) / each)


def swiss_grid_slide(cv, box, p, cols=6, rows=2, rule=0.3, labels=None, font=None, fills=None,
                     ink=demo.INK, line=demo.MUTED, bar=None, ease=vb.ease_out_expo, stagger=0.45):
    """Draw the grid slide in `box` at progress `p` (0 -> 1).

    The first 30% draws the grid: `cols` x `rows` hairline cells and a heavy
    rule at `rule` (a fraction of the box height) wiping left to right. Then
    each column's panel slides up from the bottom edge to fill from the rule
    down (`fills[i]`, default a muted tint), and `labels[i]` (one short string
    per column, in `font`) drops onto the rule above it, column by column with
    `stagger`. `bar` gives each panel a short accent line near its top.
    Returns the column Boxes (below the rule), for laying more on the grid."""
    x, y, w, h = box.x, box.y, box.w, box.h
    cw = w / cols
    ry = y + h * rule
    grid = ease(vb.clamp01(p / 0.3))
    for c in range(cols + 1):          # verticals grow downwards, left to right
        g = vb.clamp01(grid * 1.6 - c / cols * 0.6)
        if g > 0:
            cv.line(x + c * cw, y, x + c * cw, y + h * g, line, width=1, alpha=0.35)
    for r in range(rows + 1):          # horizontals reach across from the left
        g = vb.clamp01(grid * 1.6 - r / rows * 0.6)
        ly = ry + (y + h - ry) * r / rows if r else y
        if g > 0:
            cv.line(x, ly, x + w * g, ly, line, width=1, alpha=0.35)
    columns = []
    for i in range(cols):
        cx = x + i * cw
        q = ease(column_progress(p, i, cols, stagger=stagger))
        cell = vb.Box(cx, ry, cw, y + h - ry)
        columns.append(cell)
        if q > 0:
            top = ry + (y + h - ry) * (1 - q)
            with cv.clip(cx, ry, cw, y + h - ry):
                fill = fills[i] if fills else line
                cv.rect(cx + 1, top, cw - 2, y + h - top, fill, alpha=1.0 if fills else 0.25)
                if bar:
                    cv.rect(cx + cw * 0.15, top + 22, cw * 0.5, 4, bar, radius=2)
        if labels and font and q > 0:
            text = labels[i]
            _, th = vb.text.block_size([text], font)
            drop = (1 - q) * th * 1.2
            vb.text.draw(cv, [text], font, cx + 10, ry - th - 6 - drop, ink, alpha=q)
    rule_w = vb.ease_in_out_quart(vb.clamp01((p - 0.08) / 0.3))
    if rule_w > 0:
        cv.rect(x, ry - 2, w * rule_w, 4, ink)
    return columns


def draw(n, cv):
    box = vb.Box(120, 90, demo.W - 240, demo.H - 170)
    fills = [demo.ACCENT] + ['#2c3a44', '#30424c', '#344a54', '#38525c', '#3c5a64']
    cols = swiss_grid_slide(cv, box, demo.phase(n, 0.15, 2.5), labels=list('RASTER'), font=demo.font(84, 800),
                            fills=fills, bar=demo.TEAL)
    cv.mark('grid', box.x, box.y, box.w, box.h)
    cv.mark('first column', *cols[0])


CAPABILITY = Capability(
    id='swiss-grid-slide',
    name='Swiss grid slide',
    family='shapes',
    group='Geometric & Swiss style',
    aliases=('modular grid reveal', 'International Typographic grid motion', 'grid column reveal'),
    definition='A thin modular grid draws itself in, a bold rule sweeps across it, and blocks and letters '
               'slide one column at a time into the cells so the layout locks onto the grid.',
    phrasings=('build the title on a visible Swiss-style grid, column by column',
               'grid lines appear, then each column slides up into place with a letter on top',
               'a modernist layout where the columns snap into a ruled grid one after another'),
    related=('tile-grid-title-reveal', 'bento-grid-reveal', 'tile-flip', 'staggered-cascade-reveal',
             'small-multiples-cascade', 'uncover'),
    api=('videobuilder.capabilities.shapes.swiss_grid_slide.swiss_grid_slide',
         'videobuilder.capabilities.shapes.swiss_grid_slide.column_progress'),
    demo=lambda: demo.film(draw),
)

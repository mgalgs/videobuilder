"""Row collapse removal: a deleted list row fades and squeezes to zero height
while the rows beneath it slide up to close the gap."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def collapse_rows(heights, removed, p, gap=0, fade=0.7, ease=vb.ease_in_out_quart):
    """The layout of a list while row `removed` collapses, at progress `p`
    (0 -> 1). `heights` are the rows' full heights, top to bottom, `gap` the
    space between them. Returns `(rows, total)`: `rows` holds `(top, height,
    alpha)` per row, `top` measured from the list's top; `total` is the
    list's current height. The removed row fades out over the first `fade`
    of the move while its height (and the gap after it) shrinks to nothing
    on `ease`, so the rows below rise by exactly that much."""
    p = vb.clamp01(p)
    shrink = ease(p)
    rows, top = [], 0.0
    for i, h in enumerate(heights):
        if i == removed:
            alpha = 1 - vb.clamp01(p / fade) if fade > 0 else float(p < 1)
            h, g = h * (1 - shrink), gap * (1 - shrink)
            rows.append((top, h, alpha))
        else:
            alpha, g = 1.0, gap
            rows.append((top, h, alpha))
        top += h + (g if i < len(heights) - 1 else 0)
    return rows, top


def draw_collapsing_list(cv, x, y, w, heights, removed, p, draw_row, gap=0, **kw):
    """Draw a list at (x, y), `w` wide, with row `removed` collapsing at
    progress `p` (see `collapse_rows`, which `kw` goes to). `draw_row(cv, i,
    box)` paints row `i` into its full-height `box`; the collapsing row is
    clipped to its shrinking slot, its content staying centred in it, and
    faded. Returns the Box the list occupies now."""
    rows, total = collapse_rows(heights, removed, p, gap=gap, **kw)
    for i, ((top, h, alpha), full) in enumerate(zip(rows, heights)):
        if alpha <= 0 or h <= 0.5:
            continue
        box = vb.Box(x, y + top - (full - h) / 2, w, full)
        if i == removed:
            with cv.clip(x - 40, y + top, w + 80, h), cv.layer(opacity=alpha):
                draw_row(cv, i, box)
        else:
            draw_row(cv, i, box)
    return vb.Box(x, y, w, total)


# ---- demo ----

ROW_H, GAP, PAD, LIST_W = 58, 10, 14, 440
ROWS = 5
GONE = 2
SELECT_AT, START, END = 1.0, 1.6, 2.6  # the poster (0.7 of 3 s = 2.1 s) lands mid-collapse
FADE = 1.0  # fade over the whole move, so mid-collapse the row is still plainly there
WIDTHS = (0.42, 0.5, 0.46, 0.58, 0.38)


def _row(cv, i, box, p_select):
    hot = i == GONE and p_select > 0
    x, y, w, h = box
    fill = kit.mix('#1f2128', '#3a2226', p_select) if i == GONE else '#1f2128'
    cv.rect(x, y, w, h, fill, radius=12)
    cv.outline(x, y, w, h, demo.ACCENT if hot else demo.LINE, width=1.5, radius=12,
               alpha=p_select if hot else 1.0)
    cv.rect(x + 14, y + 13, 32, 32, demo.ACCENT if i == GONE else '#33363f', radius=8)
    cv.rect(x + 60, y + 18, (w - 130) * WIDTHS[i], 8, demo.INK, radius=4, alpha=0.85)
    cv.rect(x + 60, y + 34, (w - 130) * WIDTHS[i] * 0.6, 6, demo.MUTED, radius=3, alpha=0.7)
    if hot:  # the delete button that was "pressed"
        bx, by = x + w - 44, y + 15
        cv.rect(bx, by, 28, 28, demo.ACCENT, radius=7, alpha=p_select)
        cv.rect(bx + 8, by + 8, 12, 3, demo.INK, radius=1.5, alpha=p_select)
        cv.rect(bx + 9, by + 12, 10, 9, demo.INK, radius=2, alpha=p_select)
    else:
        for k in range(3):
            demo.dot(cv, x + w - 30, y + h / 2 - 8 + 8 * k, r=2.2, color=demo.MUTED)


def draw(n, cv):
    p_select = demo.phase(n, SELECT_AT, SELECT_AT + 0.25)
    p = demo.phase(n, START, END)
    heights = [ROW_H] * ROWS
    _, total = collapse_rows(heights, GONE, p, gap=GAP, fade=FADE)
    full = ROWS * ROW_H + (ROWS - 1) * GAP
    x = (demo.W - LIST_W) / 2
    y = (demo.H - full) / 2
    pw, ph = LIST_W + 2 * PAD, total + 2 * PAD
    cv.shadow(x - PAD, y - PAD, pw, ph, radius=20, dy=10, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(x - PAD, y - PAD, pw, ph, '#191a20', radius=20)
    box = draw_collapsing_list(cv, x, y, LIST_W, heights, GONE, p,
                               lambda c, i, b: _row(c, i, b, p_select), gap=GAP, fade=FADE)
    cv.mark('list', *box)


CAPABILITY = Capability(
    id='row-collapse-removal',
    name='Row collapse removal',
    family='ui',
    group='Gestures & drag',
    aliases=('list item collapse', 'height collapse delete', 'collapse on delete'),
    definition='A deleted row in a list fades and flattens to nothing, and the rows below it '
               'glide up to fill the space it left.',
    phrasings=('when I delete an item the list should close up smoothly',
               'the row squishes away and everything underneath slides up',
               'remove a list entry without the rest of the list jumping'),
    related=('accordion-height-expand', 'bottom-sheet-slide-up', 'leaderboard-row-swap',
             'hover-reveal-actions', 'accordion-fold', 'dropdown-stagger-reveal'),
    api=('videobuilder.capabilities.ui.row_collapse_removal.draw_collapsing_list',
         'videobuilder.capabilities.ui.row_collapse_removal.collapse_rows'),
    demo=lambda: demo.film(draw),
)

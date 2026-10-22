"""Segmented control slide: a row of options in one track, with a highlight
pill that slides from the old choice to the new one and stretches or shrinks
to fit the new label on the way."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def segments(labels, font, cx, cy, pad=40, height=None, inset=8):
    """Lay out a segmented control centred at (cx, cy): returns `(track,
    cells)`, the track's Box and one Box per label, each as wide as its label
    plus `pad` either side. `height` defaults to the font's line height plus
    padding; the cells sit `inset` inside the track."""
    widths = [vb.text.measure(t, font) + 2 * pad for t in labels]
    h = height or vb.text.line_height(font) + pad
    tw = sum(widths) + 2 * inset
    x, y = cx - tw / 2 + inset, cy - h / 2
    cells = []
    for w in widths:
        cells.append(vb.Box(x, y, w, h))
        x += w
    return vb.Box(cx - tw / 2, y - inset, tw, h + 2 * inset), cells


def pill_box(a, b, p, ease=vb.ease_out_quint, stretch=0.2):
    """The highlight between cell Box `a` and cell Box `b` at progress `p`
    (0 -> 1). Both edges ease to the new cell, the leading edge a little ahead
    of the trailing one (`stretch`, a fraction of the move), so the pill
    stretches as it travels and resizes to the new label as it lands."""
    p = vb.clamp01(p)
    lead = ease(vb.clamp01(p / (1 - stretch)))
    trail = ease(vb.clamp01((p - stretch) / (1 - stretch)))
    right = b.x >= a.x
    lx = a.x + (b.x - a.x) * (trail if right else lead)
    rx = a.x + a.w + (b.x + b.w - a.x - a.w) * (lead if right else trail)
    return vb.Box(lx, b.y, rx - lx, b.h)


def draw_segmented_control(cv, labels, font, cx, cy, selected, previous=None, p=1.0,
                           track='#23252d', pill=demo.ACCENT, ink=demo.INK, muted=demo.MUTED,
                           ease=vb.ease_out_quint, stretch=0.2, **kw):
    """Draw a segmented control centred at (cx, cy) with its pill moving from
    option `previous` to option `selected` (indices into `labels`) at
    progress `p`. Labels the pill covers read in `ink`, the rest in `muted`.
    `kw` goes to `segments`. Returns `(track, pill)` Boxes."""
    tbox, cells = segments(labels, font, cx, cy, **kw)
    a = cells[selected if previous is None else previous]
    box = pill_box(a, cells[selected], p, ease, stretch)
    r = tbox.h / 2
    cv.rect(*tbox, track, radius=r)
    cv.outline(*tbox, demo.LINE, width=2, radius=r)
    cv.shadow(*box, radius=box.h / 2, dy=4, blur=14, color=(0, 0, 0, 0.35))
    cv.rect(*box, pill, radius=box.h / 2)
    for text, cell in zip(labels, cells):
        lo, hi = max(cell.x, box.x), min(cell.x + cell.w, box.x + box.w)
        cover = vb.clamp01((hi - lo) / cell.w)  # how much of this label the pill sits under
        demo.word(cv, text, cell.x + cell.w / 2, cell.y + cell.h / 2, font=font, color=muted)
        if cover > 0:
            demo.word(cv, text, cell.x + cell.w / 2, cell.y + cell.h / 2, font=font, color=ink, alpha=cover)
    return tbox, box


def _cursor(cv, x, y, s=1.0, alpha=1.0):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK, alpha))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG, alpha))
    c.set_line_width(2.5)
    c.stroke()
    c.restore()


LABELS = ('Day', 'Week', 'This month')
STEPS = ((0, 2, 0.75), (2, 1, 1.85))  # (from, to, click time in seconds)


def draw(n, cv):
    f = demo.font(44, 700)
    cx, cy = demo.W / 2, demo.H / 2
    _, cells = segments(LABELS, f, cx, cy)
    t = n / demo.FPS
    selected, previous, p = 0, None, 1.0
    for a, b, at in STEPS:
        if t >= at:
            selected, previous, p = b, a, demo.phase(n, at, at + 0.6)
    tbox, box = draw_segmented_control(cv, LABELS, f, cx, cy, selected, previous, p)
    cv.mark('pill', *box)
    cv.mark('control', *tbox)
    # the pointer glides to each option just before it is clicked, and dips as it clicks
    spots = [(c.x + c.w * 0.62, c.y + c.h * 0.6) for c in cells]
    x, y, left = spots[1][0] + 40, cy + 160, 0.1
    for _, b, at in STEPS:
        q = vb.ease_in_out_quart(demo.phase(n, left, at - 0.08))
        x, y = x + (spots[b][0] - x) * q, y + (spots[b][1] - y) * q
        left = at + 0.3
    press = max((1 - abs(t - at) / 0.12 for _, _, at in STEPS), default=0)
    _cursor(cv, x, y, s=1.4 - 0.25 * max(0.0, press))


CAPABILITY = Capability(
    id='segmented-control-slide',
    name='Segmented control slide',
    family='ui',
    group='Toggles & controls',
    aliases=('sliding pill selector', 'toggle group thumb', 'segmented picker'),
    definition='When a different option in a row of choices is picked, the coloured highlight behind '
               'the current one slides across to it and stretches or narrows to fit its label.',
    phrasings=('the highlight slides over to the option I click, like an iOS segmented control',
               'a pill that moves between Day, Week and Month and changes width to fit each one',
               'tab switcher where the selected background glides to the new tab'),
    related=('pagination-pill-indicator', 'tooltip-fade-follow', 'arrow-slide', 'tab-panel-slide',
             'carousel-slide', 'before-after-slider'),
    api=('videobuilder.capabilities.ui.segmented_control_slide.draw_segmented_control',
         'videobuilder.capabilities.ui.segmented_control_slide.pill_box',
         'videobuilder.capabilities.ui.segmented_control_slide.segments'),
    demo=lambda: demo.film(draw),
)

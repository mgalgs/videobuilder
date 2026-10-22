"""Hover-reveal actions: a row sits clean until the pointer rests on it, then
its action buttons slide in at the row's end, one after another, and leave
again when the pointer moves on."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def hover(t, enter, leave=None, rise=0.4, fall=0.2):
    """How hovered something is at time `t` (seconds), 0 -> 1: eases in over
    `rise` seconds from `enter`, and back out over `fall` from `leave` (never,
    if None). Feed it to `reveal_actions` and to the row's highlight."""
    p = vb.ease_out_quint(vb.clamp01((t - enter) / rise))
    if leave is not None:
        p *= 1 - vb.ease_in_out_quart(vb.clamp01((t - leave) / fall))
    return p


def reveal_actions(cv, right, cy, labels, p, font=None, colors=None, ink=demo.INK, gap=8, pad=14,
                   height=34, slide=18, stagger=0.18):
    """Draw action pills (one per label) right-aligned so the last ends at
    `right`, vertically centred on `cy`, at reveal progress `p` (0 hidden ->
    1 shown). Each fades in while sliding `slide` px in from the right, the
    leftmost first, `stagger` of the reveal apart. `colors` gives each pill's
    fill (default: a quiet grey). Returns the pills' Boxes, left to right."""
    f = font or demo.font(15, 700)
    colors = colors or ['#2f323b'] * len(labels)
    widths = [vb.text.measure(s, f) + 2 * pad for s in labels]
    x = right - sum(widths) - gap * (len(labels) - 1)
    span = 1 - stagger * (len(labels) - 1) if len(labels) > 1 else 1
    boxes = []
    for i, (label, w, color) in enumerate(zip(labels, widths, colors)):
        q = vb.ease_out_quint(vb.clamp01((p - i * stagger) / max(span, 1e-6)))
        box = vb.Box(x, cy - height / 2, w, height)
        if q > 0:
            with cv.layer(opacity=q, dx=slide * (1 - q)):
                cv.rect(box.x, box.y, w, height, color, radius=height / 2)
                lw, lh = vb.text.block_size([label], f)
                vb.text.draw(cv, [label], f, box.x + (w - lw) / 2, cy - lh / 2, ink)
        boxes.append(box)
        x += w + gap
    return boxes


def pointer(cv, x, y, size=24, color=demo.INK):
    """An arrow cursor with its tip at (x, y)."""
    s = size / 34
    pts = [(0, 0), (0, 30), (8, 23), (13, 34), (18, 32), (13, 21), (23, 21)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    cv.shape_shadow(pts, dy=2, blur=4, color=(0, 0, 0, 0.5))
    cv.shape_shadow(pts, color=color)


ROWS = ('Quarterly report.pdf', 'Launch plan.key', 'Team photo.jpg')
ROW_W, ROW_H, ROW_GAP = 640, 68, 14
X0 = (demo.W - ROW_W) / 2
Y0 = (demo.H - 3 * ROW_H - 2 * ROW_GAP) / 2
# (row, enter, leave): the pointer rests on row 1, then moves down to row 2
VISITS = ((1, 0.75, 1.75), (2, 1.95, None))
PATH = ((0.0, X0 + ROW_W * 0.42, demo.H + 30), (0.7, X0 + ROW_W * 0.42, Y0 + 1.5 * ROW_H + ROW_GAP),
        (1.7, X0 + ROW_W * 0.42, Y0 + 1.5 * ROW_H + ROW_GAP), (2.0, X0 + ROW_W * 0.47, Y0 + 2.5 * ROW_H + 2 * ROW_GAP))


def draw(n, cv):
    t = n / demo.FPS
    name = demo.font(21, 600)
    for i, label in enumerate(ROWS):
        y = Y0 + i * (ROW_H + ROW_GAP)
        h = max((hover(t, e, l) for r, e, l in VISITS if r == i), default=0.0)
        cv.rect(X0, y, ROW_W, ROW_H, kit.mix('#1d1f25', '#272a32', h), radius=12)
        cv.outline(X0, y, ROW_W, ROW_H, kit.mix(demo.LINE, '#4a4e58', h), width=1.5, radius=12)
        cv.rect(X0 + 20, y + ROW_H / 2 - 16, 32, 32, demo.TEAL, radius=8, alpha=0.85)
        lw, lh = vb.text.block_size([label], name)
        vb.text.draw(cv, [label], name, X0 + 70, y + (ROW_H - lh) / 2, demo.INK)
        boxes = reveal_actions(cv, X0 + ROW_W - 18, y + ROW_H / 2, ('Share', 'Rename', 'Delete'), h,
                               colors=('#363a44', '#363a44', demo.ACCENT))
        if h > 0.5:
            cv.mark(f'actions-{i}', boxes[0].x, boxes[0].y, boxes[-1].x + boxes[-1].w - boxes[0].x, boxes[0].h)
    k = next(j for j in range(len(PATH) - 1) if t < PATH[j + 1][0] or j == len(PATH) - 2)
    (t0, xa, ya), (t1, xb, yb) = PATH[k], PATH[k + 1]
    q = vb.ease_in_out_quart(vb.clamp01((t - t0) / (t1 - t0)))
    pointer(cv, xa + (xb - xa) * q, ya + (yb - ya) * q)


TECHNIQUE = Technique(
    id='hover-reveal-actions',
    name='Hover-reveal actions',
    family='ui',
    group='Overlays & menus',
    aliases=('hover actions', 'reveal on hover', 'row actions on hover', 'hover toolbar'),
    definition='Buttons for acting on an item stay hidden until the pointer rests on it, then slide '
               'and fade in at its edge, and tuck away again when the pointer leaves.',
    phrasings=('when the mouse goes over a row, the edit and delete buttons show up',
               'the action buttons only appear when you hover over the item',
               'hovering a list item pops out its little toolbar'),
    related=('swipe-action-row', 'image-hover-mask-reveal', 'hover-lift', 'spotlight-hover',
             'icon-hover-bounce', 'fade-up-scroll-reveal'),
    api=('videobuilder.techniques.ui.hover_reveal_actions.reveal_actions',
         'videobuilder.techniques.ui.hover_reveal_actions.hover',
         'videobuilder.techniques.ui.hover_reveal_actions.pointer'),
    demo=lambda: demo.film(draw),
)

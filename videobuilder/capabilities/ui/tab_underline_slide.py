"""Tab underline slide: the bar under the selected tab glides to the newly
picked tab, its leading end running ahead and its trailing end catching up,
so it stretches mid-move and lands at the new tab's width."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def underline_span(spans, src, dst, p, stretch=0.3, ease=vb.ease_in_out_quart):
    """The underline's `(x, w)` at progress `p` (0 -> 1) of a move from tab
    `src` to tab `dst`. `spans` is each tab's `(x, w)`. The edge on the side
    it travels towards runs over the first `1 - stretch` of the move and the
    other edge over the last `1 - stretch`, so the bar lengthens then
    shortens; `stretch=0` slides it rigidly, resizing as it goes."""
    (x0, w0), (x1, w1) = spans[src], spans[dst]
    lead = ease(vb.clamp01(p / (1 - stretch))) if stretch < 1 else ease(p)
    lag = ease(vb.clamp01((p - stretch) / (1 - stretch))) if stretch < 1 else ease(p)
    fwd = x1 >= x0
    left = x0 + (x1 - x0) * (lead if not fwd else lag)
    right = x0 + w0 + (x1 + w1 - x0 - w0) * (lag if not fwd else lead)
    return left, max(0.0, right - left)


def draw_tab_bar(cv, labels, font, x, y, src, dst, p, gap=72, color=kit.ACCENT, ink=kit.INK,
                 muted=kit.MUTED, track=kit.LINE, thickness=6, drop=22, **kw):
    """A row of tab `labels` from top-left (x, y), `gap` apart, with its
    underline sliding from tab `src` to tab `dst` at progress `p`. Each label
    brightens from `muted` to `ink` as the bar covers it; a thin `track` runs
    under the whole row. `kw` goes to `underline_span`. Returns the Box of
    each label."""
    boxes, left = [], x
    for label in labels:
        w, h = vb.text.block_size([label], font)
        boxes.append(vb.Box(left, y, w, h))
        left += w + gap
    base = y + boxes[0].h + drop
    cv.rect(x, base, left - gap - x, 2, track)
    bx, bw = underline_span([(b.x, b.w) for b in boxes], src, dst, p, **kw)
    for label, b in zip(labels, boxes):
        cover = vb.clamp01((min(bx + bw, b.x + b.w) - max(bx, b.x)) / b.w)
        vb.text.draw(cv, [label], font, b.x, b.y, kit.mix(muted, ink, cover))
    cv.rect(bx, base - thickness / 2 + 1, bw, thickness, color, radius=thickness / 2)
    cv.mark('underline', bx, base - thickness / 2 + 1, bw, thickness)
    return boxes


LABELS = ('Overview', 'Files', 'Activity & updates')
MOVES = ((0, 1, 0.5, 1.2), (1, 2, 1.7, 2.4))   # (from, to, start s, end s)


def draw(n, cv):
    f = demo.font(44, 700)
    widths = [vb.text.block_size([t], f)[0] for t in LABELS]
    total = sum(widths) + 72 * (len(LABELS) - 1)
    x, y = (demo.W - total) / 2, demo.H / 2 - 50
    cv.shadow(x - 56, y - 52, total + 112, 190, radius=24, dy=10, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(x - 56, y - 52, total + 112, 190, '#1b1d23', radius=24)
    src, dst, p = 0, 0, 0.0
    for a, b, t0, t1 in MOVES:
        if n / demo.FPS >= t0:
            src, dst, p = a, b, demo.phase(n, t0, t1)
    draw_tab_bar(cv, LABELS, f, x, y, src, dst, p)


CAPABILITY = Capability(
    id='tab-underline-slide',
    name='Tab underline slide',
    family='ui',
    group='Toggles & controls',
    aliases=('tab indicator slide', 'sliding tab bar', 'sliding tab indicator'),
    definition='When another tab is chosen, the coloured line under the current tab glides across to it, '
               'stretching out on the way and settling to the new tab\'s width.',
    phrasings=('the highlight bar under the tabs slides over to the one I click',
               'move the tab underline to the next tab instead of just jumping',
               'a stretchy indicator line that follows the selected tab'),
    related=('tab-panel-slide', 'underline-wipe', 'bottom-sheet-slide-up', 'indeterminate-bar',
             'input-underline-grow', 'lower-third-slide-in-bar'),
    api=('videobuilder.capabilities.ui.tab_underline_slide.draw_tab_bar',
         'videobuilder.capabilities.ui.tab_underline_slide.underline_span'),
    demo=lambda: demo.film(draw),
)

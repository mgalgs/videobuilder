"""Sticky Card Stack on Scroll: a column of cards scrolls up a viewport, and
each one sticks when it reaches the top, so the next card slides up over it
and the pinned cards pile into a stack."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def sticky_stack_layout(scroll, count, pitch, start=0.0, top=0.0, peek=0.0):
    """Where each of `count` cards sits at scroll offset `scroll`.

    Card `i` lies in the content at `start + i * pitch` and sticks once it
    has scrolled up to `top + i * peek` (so `peek` leaves a sliver of each
    pinned card showing above the next). Returns one `(y, depth)` per card:
    `y` is its top edge in viewport coordinates, `depth` how many later cards
    have slid over it (fractional while one is on its way), for shrinking or
    dimming the buried ones."""
    ys = [max(start + i * pitch - scroll, top + i * peek) for i in range(count)]
    out = []
    for i, y in enumerate(ys):
        depth = sum(vb.clamp01(1 - (ys[j] - top - j * peek) / pitch) for j in range(i + 1, count))
        out.append((y, depth))
    return out


def stack_scroll_end(count, card_h, gap=24.0, peek=12.0):
    """The scroll offset at which the last of `count` cards pins: scroll
    from 0 to this to play the whole stack."""
    return (count - 1) * (card_h + gap - peek)


def sticky_card_stack(cv, x, y, w, h, scroll, count, draw_card, card_h, gap=24.0, pad=24.0, peek=12.0,
                      shrink=0.04, dim=0.22, radius=0):
    """Draw a sticky card stack inside the viewport (x, y, w, h), clipped to it.

    `scroll` is the content offset in pixels; cards are `card_h` tall with
    `gap` between them, `pad` from the viewport's top and sides.
    `draw_card(cv, i, cx, cy, cw, ch)` draws card `i` centred at (cx, cy).
    Buried cards shrink by `shrink` and darken by `dim` per card above them.
    Returns the scroll at which the last card pins (`stack_scroll_end`)."""
    cw = w - 2 * pad
    layout = sticky_stack_layout(scroll, count, card_h + gap, start=pad, top=pad, peek=peek)
    with cv.clip(x, y, w, h, radius=radius):
        for i, (cy, depth) in enumerate(layout):
            s = max(0.0, 1 - shrink * depth)
            # Shrink toward the card's top edge, so its pinned sliver stays put.
            cx, mid = x + w / 2, y + cy + card_h * s / 2
            draw_card(cv, i, cx, mid, cw * s, card_h * s)
            if dim and depth > 0:
                cv.rect(cx - cw * s / 2, mid - card_h * s / 2, cw * s, card_h * s, '#000000',
                        radius=18 * s, alpha=min(0.7, dim * depth))
    return stack_scroll_end(count, card_h, gap, peek)


COLORS = (demo.TEAL, '#7b8cff', '#e8b44a', demo.ACCENT)
VIEW_X, VIEW_Y, VIEW_W, VIEW_H = demo.W / 2 - 200, 40, 400, demo.H - 80
CARD_H, GAP, PAD, PEEK = 190, 22, 22, 12


def _card(cv, i, cx, cy, cw, ch):
    demo.card(cv, cx, cy, w=cw, h=ch, color=COLORS[i % len(COLORS)])


def draw(n, cv):
    count = len(COLORS)
    end = stack_scroll_end(count, CARD_H, GAP, PEEK)
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.7))
    cv.rect(VIEW_X, VIEW_Y, VIEW_W, VIEW_H, '#1c1e25', radius=22)
    cv.outline(VIEW_X, VIEW_Y, VIEW_W, VIEW_H, demo.LINE, width=2, radius=22)
    sticky_card_stack(cv, VIEW_X, VIEW_Y, VIEW_W, VIEW_H, end * p, count, _card, CARD_H,
                      gap=GAP, pad=PAD, peek=PEEK, radius=22)
    # A scrollbar, so the motion reads as the page scrolling.
    track = VIEW_H - 40
    thumb = track * 0.35
    cv.rect(VIEW_X + VIEW_W + 14, VIEW_Y + 20 + (track - thumb) * p, 5, thumb, demo.MUTED, radius=3)


CAPABILITY = Capability(
    id='sticky-card-stack-on-scroll',
    name='Sticky card stack on scroll',
    family='ui',
    group='Scroll',
    aliases=('stacking cards', 'layered scroll cards', 'sticky stacking cards'),
    definition='As a page scrolls, each card stops when it reaches the top and the next card '
               'rides up over it, so the cards pile into a stack instead of leaving the screen.',
    phrasings=('cards that stick at the top and stack on each other as you scroll',
               'scroll a list where every card pins and the next one covers it',
               'the stacking-cards scroll effect for a feature list'),
    related=('stacked-card-reveal', 'card-deck-fan', 'roll-up', 'infinite-scroll-append',
             'stacked-line-build', 'end-card-with-subscribe-slot'),
    api=('videobuilder.capabilities.ui.sticky_card_stack_on_scroll.sticky_card_stack',
         'videobuilder.capabilities.ui.sticky_card_stack_on_scroll.sticky_stack_layout'),
    demo=lambda: demo.film(draw),
)

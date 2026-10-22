"""Pagination pill indicator: a row of page dots where the current page's dot
is drawn long and coloured, and as the page changes that pill shrinks back to
a dot while the next one grows, so the highlight seems to glide along the row."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def pill_widths(count, page, dot=16, pill=56):
    """The width of each of `count` indicators when the view sits at `page`, a
    float page index (1.4 is 40% of the way from page 1 to page 2). A dot
    within one page of `page` stretches toward `pill` in proportion; the
    widths always sum to the same total, so the row never changes length."""
    page = min(max(page, 0), count - 1)
    return [dot + (pill - dot) * max(0.0, 1 - abs(i - page)) for i in range(count)]


def draw_pagination(cv, cx, cy, count, page, dot=16, pill=56, gap=14, color=demo.ACCENT, idle=demo.LINE):
    """Draw the indicator row centred at (cx, cy) for float `page` (see
    `pill_widths`): the active pill in `color`, the rest as `idle` dots, each
    blending between the two as it stretches. Drive `page` with an eased
    0 -> 1 step per page turn for the gliding look. Returns the row's Box."""
    widths = pill_widths(count, page, dot, pill)
    total = sum(widths) + gap * (count - 1)
    x, y = cx - total / 2, cy - dot / 2
    for w in widths:
        t = (w - dot) / (pill - dot)
        cv.rect(x, y, w, dot, kit.mix(idle, color, t), radius=dot / 2)
        x += w + gap
    box = vb.Box(cx - total / 2, y, total, dot)
    cv.mark('pagination', *box)
    return box


PAGES = 4
TURNS = (0.5, 1.2, 1.9)  # seconds each page turn starts
TURN = 0.45


def page_at(n):
    """The demo's float page at frame `n`: three eased turns, 0 -> 3."""
    return sum(vb.ease_in_out_quart(demo.phase(n, s, s + TURN)) for s in TURNS)


def draw(n, cv):
    page = page_at(n)
    cy = demo.H / 2 - 40
    for i in range(PAGES):
        off = i - page
        demo.card(cv, demo.W / 2 + off * 360, cy, w=320, h=200, color=demo.TEAL if i % 2 else '#3a3d47',
                  alpha=1 - 0.7 * min(1, abs(off)))
    draw_pagination(cv, demo.W / 2, demo.H - 110, PAGES, page, dot=18, pill=66, gap=16)


CAPABILITY = Capability(
    id='pagination-pill-indicator',
    name='Pagination pill indicator',
    family='ui',
    group='Feedback & status',
    aliases=('dot pagination', 'active dot stretch', 'expanding dots indicator'),
    definition='A row of small page dots in which the current page shows as a longer coloured capsule, '
               'which shrinks back as its neighbour lengthens whenever the page turns.',
    phrasings=('the little dots under a carousel where the active one is a stretched bar',
               'page dots that grow into a pill on the selected slide',
               'an onboarding swiper indicator where the highlight slides to the next dot'),
    related=('segmented-control-slide', 'cursor-follower-dot-and-ring', 'scrollspy-nav-indicator',
             'cursor-state-change', 'dot-density-map', 'bouncing-dots'),
    api=('videobuilder.capabilities.ui.pagination_pill_indicator.draw_pagination',
         'videobuilder.capabilities.ui.pagination_pill_indicator.pill_widths'),
    demo=lambda: demo.film(draw),
)

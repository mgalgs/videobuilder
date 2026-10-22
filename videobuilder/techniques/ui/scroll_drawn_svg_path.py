"""Scroll-drawn SVG path: a line laid out down a long page draws itself as
the page scrolls, its pen tip held on a fixed line of the viewport so the
stroke seems to follow the reader down. The partial stroke is
`vb.paths.reveal`; this module adds the tie between scroll and how much is
drawn."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def fraction_at_y(points, y):
    """The arc-length fraction (0..1) of `points` at the first place the path
    reaches page height `y`: 0 above its start, 1 once `y` is past its end.
    Meant for a path that runs down the page (y mostly increasing)."""
    if len(points) < 2 or y <= points[0][1]:
        return 0.0
    total = vb.paths.length(points)
    if total == 0:
        return 1.0
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        hop = math.hypot(x1 - x0, y1 - y0)
        if y1 >= y > y0:
            return (acc + hop * (y - y0) / (y1 - y0)) / total
        acc += hop
    return 1.0


def draw_scroll_path(cv, points, scroll, anchor, color, width=6, ghost=None, ghost_alpha=0.18, pen=None):
    """Draw `points` (page coordinates) on a page scrolled down by `scroll`
    px, revealed up to where the path crosses the viewport line `anchor` px
    from the top, so the drawn tip rides that line while the page moves.
    `ghost`: a colour to trace the whole path faintly underneath. `pen`: a
    radius for a dot at the tip. Returns the tip's screen point, or None
    before the path starts."""
    shown = [(x, y - scroll) for x, y in points]
    if ghost:
        vb.paths.draw(cv, shown, ghost, width=width, alpha=ghost_alpha)
    drawn = vb.paths.reveal(shown, fraction_at_y(points, scroll + anchor))
    vb.paths.draw(cv, drawn, color, width=width)
    if not drawn:
        return None
    if pen:
        demo.dot(cv, *drawn[-1], r=pen, color=color)
    return drawn[-1]


# ---- demo: a long page scrolls up; the winding line draws itself as it goes ----

PAGE = demo.H * 3.2                 # page height, px
ANCHOR = demo.H * 0.55              # the viewport line the pen tip rides
TOP, BOTTOM = ANCHOR - 20, PAGE - 160  # where the line starts and ends on the page: unscrolled, nearly nothing drawn


def _route():
    pts = []
    for i in range(241):
        t = i / 240
        y = TOP + (BOTTOM - TOP) * t
        pts.append((demo.W / 2 + 250 * math.sin(t * math.pi * 4.5) * min(1, t * 6), y))
    return pts


ROUTE = _route()
SCROLL = vb.ease.bezier(0.4, 0, 0.6, 1)                  # a steady scroll that starts and stops gently
STOPS = [(0.18, -1), (0.4, 1), (0.62, -1), (0.84, 1)]   # (where along the page, which side) for content cards


def draw(n, cv):
    scroll = SCROLL(demo.phase(n, 0.3, 2.7)) * (PAGE - demo.H)
    cv.rect(0, -scroll, demo.W, 90, demo.LINE)            # a page header that scrolls away
    demo.word(cv, 'Our journey', demo.W / 2, 45 - scroll, size=36)
    for at, side in STOPS:
        y = TOP + (BOTTOM - TOP) * at
        demo.card(cv, demo.W / 2 - side * 250, y - scroll, w=220, h=120, color=demo.TEAL, alpha=0.9)
    tip = draw_scroll_path(cv, ROUTE, scroll, ANCHOR, demo.ACCENT, width=7, ghost=demo.MUTED, pen=11)
    if tip:
        cv.mark('pen', tip[0] - 11, tip[1] - 11, 22, 22)
    thumb = demo.H * demo.H / PAGE                        # the scrollbar, so the scroll reads as a scroll
    cv.rect(demo.W - 16, 8, 6, demo.H - 16, demo.LINE, radius=3)
    cv.rect(demo.W - 16, 8 + (demo.H - 16 - thumb) * scroll / (PAGE - demo.H), 6, thumb, demo.MUTED, radius=3)


TECHNIQUE = Technique(
    id='scroll-drawn-svg-path',
    name='Scroll-drawn SVG path',
    family='ui',
    group='Scroll',
    aliases=('scroll-triggered line drawing', 'scroll draw path', 'scroll-linked stroke'),
    definition='A line running down a long page fills in as the page scrolls, its leading tip '
               'keeping pace with the reader so the stroke grows exactly as far as they have read.',
    phrasings=('a line that draws itself down the page as you scroll',
               'the path traces along with the scroll, connecting each section',
               'as the page moves up, a winding stroke follows it down'),
    related=('cursor-path-animation', 'stroke-draw-on', 'stroke-draw-logo-loader', 'map-route-draw',
             'line-chart-draw-on', 'line-weave'),
    api=('videobuilder.techniques.ui.scroll_drawn_svg_path.draw_scroll_path',
         'videobuilder.techniques.ui.scroll_drawn_svg_path.fraction_at_y',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

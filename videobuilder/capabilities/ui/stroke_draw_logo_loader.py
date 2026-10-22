"""Stroke draw logo loader: a one-line mark traces itself over a faint guide,
floods with colour once the line closes, then clears and starts again for as
long as something is loading."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def logo_loader(cv, points, t, color, track=demo.LINE, width=6, closed=True, draw=0.55, fill=0.2,
                hold=0.15, fill_alpha=0.85, head=True):
    """Draw one frame of a looping logo loader for the point list `points`.
    `t` is time in loops (any float; only its fractional part matters). Each
    loop the stroke traces the path by arc length over a faint `track` during
    the first `draw` of it (eased in-out), the inside fills up to `fill_alpha`
    over the next `fill`, it holds for `hold`, then the whole mark fades out
    for the rest. `head`: a dot rides the tip while the line is drawing.
    Returns the loop phase (0 -> 1) it drew."""
    p = t % 1.0
    reveal = vb.ease_in_out_quart(vb.clamp01(p / draw))
    filled = vb.clamp01((p - draw) / fill)
    fade = 1 - vb.clamp01((p - draw - fill - hold) / max(1e-6, 1 - draw - fill - hold))
    vb.paths.draw(cv, points, track, width=width, closed=closed)
    with cv.layer(opacity=fade):
        if filled > 0:
            vb.paths.draw(cv, points, color, fill=True, alpha=fill_alpha * vb.ease_out_quint(filled))
        line = vb.paths.reveal(points, reveal, closed=closed)
        vb.paths.draw(cv, line, color, width=width)
        if head and 0 < reveal < 1 and line:
            demo.dot(cv, *line[-1], r=width * 1.1, color=color)
    return p


def star(cx, cy, r, inner=0.45, tips=5):
    """A closed star outline centred at (cx, cy), first tip pointing up: a
    stand-in single-line logo mark."""
    pts = []
    for i in range(tips * 2):
        a = -math.pi / 2 + i * math.pi / tips
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H * 0.45, demo.H * 0.27
    mark = star(cx, cy, r)
    logo_loader(cv, mark, max(0.0, n / demo.FPS - 0.2) / 2.6, demo.ACCENT)
    dots = '.' * (1 + (n // 10) % 3)
    demo.word(cv, 'Loading' + dots.ljust(3, '\u2007'), cx, cy + r + demo.H * 0.09,  # figure space: no jitter
              size=28, color=demo.MUTED, weight=600)
    cv.mark('logo', cx - r, cy - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='stroke-draw-logo-loader',
    name='Stroke draw logo loader',
    family='ui',
    group='Loaders',
    aliases=('path draw loading', 'line logo loader', 'logo trace loader'),
    definition='While something loads, a brand mark is traced out as a single moving line, '
               'fills in solid once the line meets itself, then clears and traces again.',
    phrasings=('the logo draws itself in outline as the loading animation',
               'a loading screen where our icon gets traced and then colours in',
               'loop the logo being sketched by a line until the page is ready'),
    related=('line-draw-logo-reveal', 'stroke-draw-on', 'icon-line-to-fill', 'scroll-drawn-svg-path',
             'line-chart-draw-on', 'pencil-sketch'),
    api=('videobuilder.capabilities.ui.stroke_draw_logo_loader.logo_loader',
         'videobuilder.paths.reveal',
         'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)

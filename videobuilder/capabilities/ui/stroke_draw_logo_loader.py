"""Stroke draw logo loader: the same pen tracing round each outline then
filling solid as Stroke draw-on (`../typography/stroke_draw_on.py`, which
keeps the capability) -- its own alias "path draw loading" is this loader
preset's own title, looping the trace: a one-line mark traces itself over a
faint guide, floods with colour once the line closes, then clears and starts
again for as long as something is loading. This module's own code stays (a
film may still import it), but it is no longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'stroke-draw-on'


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

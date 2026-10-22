"""Border Draw Button: a button's outline is traced on by a moving line --
here two lines setting off from opposite corners and meeting halfway round --
and once the border closes, the button lights up."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique


def outline_points(x, y, w, h, radius=0, per_corner=12):
    """A rounded rectangle as a closed point list, clockwise, starting at the
    top of its top-left corner's curve (the left edge's top end)."""
    r = max(0.0, min(radius, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + r, y + r, 180), (x + w - r, y + r, 270),
                       (x + w - r, y + h - r, 0), (x + r, y + h - r, 90)):
        for k in range(per_corner + 1):
            a = math.radians(a0 + 90 * k / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def border_draw(cv, x, y, w, h, p, color, width=3, radius=0, heads=2, tip=None, alpha=1.0):
    """Draw the border of the box (x, y, w, h) traced on to progress `p`
    (0 -> 1). The loop is split into `heads` equal runs, each starting
    evenly spaced round it from the top-left corner and drawing clockwise, so
    `heads=1` is one line going all the way round and `heads=2` is two lines
    from opposite corners that meet. `tip`: a colour for a small bright dot
    riding the front of each line while it draws (None for none)."""
    if p <= 0:
        return
    m = 200  # points per run: dense enough that the corner curves stay smooth
    loop = paths.resample(outline_points(x, y, w, h, radius), heads * m, closed=True)
    for k in range(heads):
        run = loop[k * m:(k + 1) * m] + [loop[((k + 1) * m) % len(loop)]]
        seg = paths.reveal(run, p)
        paths.draw(cv, seg, color, width=width, alpha=alpha)
        if tip and 0 < p < 1 and seg:
            demo.dot(cv, *seg[-1], r=width * 1.6, color=tip, alpha=alpha)


def draw(n, cv):
    w, h, r = 460, 132, 26
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.7))
    lit = vb.ease_out_quint(demo.phase(n, 1.7, 2.1))
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=r)              # the resting button
    cv.rect(x, y, w, h, demo.ACCENT, radius=r, alpha=0.14 * lit)       # fills in once the border closes
    border_draw(cv, x, y, w, h, p, demo.ACCENT, width=5, radius=r, tip=demo.INK)
    ink = demo.kit.mix(demo.MUTED, demo.INK, lit)
    demo.word(cv, 'Get started', demo.W / 2, demo.H / 2, size=48, weight=700, color=ink)
    cv.mark('button', x, y, w, h)


TECHNIQUE = Technique(
    id='border-draw-button',
    name='Border draw button',
    family='ui',
    group='Buttons',
    aliases=('border trace hover', 'outline draw on', 'line-draw button', 'stroke trace button'),
    definition='A thin line runs around the edge of a button, tracing its outline on, '
               'and the button brightens once the line closes the loop.',
    phrasings=('a line traces around the button border',
               'the button outline draws itself on when you hover',
               'two lines race round the edge of the button and meet'),
    related=('stroke-draw-on', 'border-glow-follow', 'button-ending', 'checkbox-check-draw',
             'icon-line-to-fill', 'line-draw-logo-reveal'),
    api=('videobuilder.techniques.ui.border_draw_button.border_draw',
         'videobuilder.techniques.ui.border_draw_button.outline_points',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

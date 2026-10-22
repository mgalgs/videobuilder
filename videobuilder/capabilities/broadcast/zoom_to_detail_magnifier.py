"""Zoom-to-detail magnifier: a round glass lens travels over a picture and,
inside its rim, shows the patch beneath it blown up, so fine detail that is
unreadable at full frame becomes legible without cutting away."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def magnifier(cv, draw, cx, cy, r, zoom=2.5, rim='#ffffff', rim_width=4, shadow=0.5, glare=True):
    """Draw a lens of radius `r` centred at (cx, cy) over the scene `draw(cv)`:
    inside the circle, `draw` is redrawn scaled by `zoom` about the lens
    centre; then a soft drop shadow, the rim and a faint glare arc on top.
    Draw the scene itself first, at 1x -- the lens only adds the close-up.

    `zoom` 1 shows plain glass (ease it up as the lens arrives). Because
    `draw` is called again, vector scenes stay sharp at any `zoom`. In a film,
    move (cx, cy) along a path, e.g.
    `draw_page(cv); magnifier(cv, draw_page, *lens_at(t), r=90, zoom=3)`."""
    if r <= 0:
        return
    if shadow > 0:
        cv.shape_shadow(_circle(cx, cy, r), dy=r * 0.08, blur=r * 0.25, color=(0, 0, 0, shadow))
    with cv.clip(cx - r, cy - r, 2 * r, 2 * r, radius=r):
        with cv.layer(dx=cx * (1 - zoom), dy=cy * (1 - zoom), scale=zoom):
            draw(cv)
        cv.sector(cx, cy, r, 0, 2 * math.pi, '#ffffff', alpha=0.04)
    if glare:
        cv.arc(cx, cy, r * 0.82, math.radians(200), math.radians(250), '#ffffff', width=r * 0.06, alpha=0.35)
    cv.arc(cx, cy, r, 0, 2 * math.pi, rim, width=rim_width)
    cv.mark('magnifier', cx - r, cy - r, 2 * r, 2 * r)


def _circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---- demo ----

PAGE = (150, 70, 660, 400)  # x, y, w, h
_ROWS = ('Q3 shipments by region, units per week, adjusted for returns',
         'North 1,204  South 988  East 1,377  West 1,052  Central 812',
         'Source: internal ledger; figures rounded to nearest unit.',
         'Week 38 saw the highest single-day volume of the quarter.')


def _page(cv):
    """A light sheet of fine print with a small bar chart -- detail too small
    to read until the lens passes over it."""
    x, y, w, h = PAGE
    cv.rect(x, y, w, h, '#ebe8e1', radius=10)
    demo.word(cv, 'Quarterly report', x + w / 2, y + 34, size=26, color='#24262d', weight=800)
    f = demo.mono(7)
    for i, row in enumerate(_ROWS * 2):
        vb.text.draw(cv, [row], f, x + 30, y + 64 + i * 13, '#5b5e66')
    # the chart: tiny bars with tiny labels; one bar is the detail
    base, bx = y + h - 40, x + 60
    heights = (60, 92, 74, 128, 110, 84, 146, 102, 70, 118)
    for i, bh in enumerate(heights):
        color = demo.ACCENT if i == 6 else demo.TEAL
        cv.rect(bx + i * 56, base - bh, 30, bh, color, radius=3)
        vb.text.draw(cv, [f'W{32 + i}'], demo.mono(7), bx + i * 56 + 6, base + 6, '#5b5e66')
    vb.text.draw(cv, ['peak 2,140'], demo.mono(7, 700), bx + 6 * 56 - 6, base - 146 - 13, demo.ACCENT)
    cv.line(x + 40, base, x + w - 40, base, '#9a9da5', width=1)


def _lens_path(t):
    """Where the lens is at `t` seconds: drifts in over the text, then glides
    to the highlighted bar and settles there."""
    stops = ((0.0, 245, 140), (1.1, 390, 150), (2.2, 561, 292), (3.0, 561, 292))
    ts = [s[0] for s in stops]
    ease = vb.bezier(0.45, 0, 0.25, 1)
    return (vb.ease.interpolate(t, ts, [s[1] for s in stops], ease=ease),
            vb.ease.interpolate(t, ts, [s[2] for s in stops], ease=ease))


def _draw(n, cv):
    t = n / demo.FPS
    _page(cv)
    grow = vb.ease_out_back(demo.phase(n, 0.0, 0.5))
    zoom = 1 + 1.6 * vb.ease_in_out_quart(demo.phase(n, 0.2, 0.9))
    cx, cy = _lens_path(t)
    magnifier(cv, _page, cx, cy, r=88 * grow, zoom=zoom)


CAPABILITY = Capability(
    id='zoom-to-detail-magnifier',
    name='Zoom-to-detail magnifier',
    family='broadcast',
    group='Annotation',
    aliases=('loupe zoom', 'magnifying glass reveal', 'magnifier lens'),
    definition='A round lens slides across a picture and, inside its rim, shows the area under it '
               'enlarged so small detail becomes readable.',
    phrasings=('put a magnifying glass over the chart so we can read the small print',
               'move a little zoom circle across the image to show the detail',
               'hover a loupe over that part of the picture'),
    related=('image-hover-zoom', 'zoom-blur', 'scale-zoom-through', 'optical-zoom', 'dock-magnification',
             'dolly-zoom'),
    api=('videobuilder.capabilities.broadcast.zoom_to_detail_magnifier.magnifier',),
    demo=lambda: demo.film(_draw),
)

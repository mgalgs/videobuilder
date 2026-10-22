"""Tooltip Fade Follow: a small label fades in when the pointer comes onto a
target, trails the pointer a beat behind while it moves, then fades out as
the pointer leaves."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))  # a pointer, tip at (0, 0)


def follow(path, t, lag=0.12, fps=30):
    """Where something trailing `path(t) -> (x, y)` sits at time `t`: each
    frame it closes the gap by the share a `lag`-second time constant gives,
    so it eases after the pointer and catches up when it stops. Worked out
    from time 0 every call, so any frame renders on its own."""
    k = 1 - math.exp(-1 / (fps * max(lag, 1e-6)))
    x, y = path(0.0)
    for i in range(1, int(round(t * fps)) + 1):
        tx, ty = path(i / fps)
        x, y = x + (tx - x) * k, y + (ty - y) * k
    return x, y


def hover(t, enter, leave, fade=0.25):
    """Tooltip opacity 0 -> 1 -> 0: fades in over `fade` seconds from `enter`,
    out over `fade` seconds from `leave` (eased both ways)."""
    p_in = vb.clamp01((t - enter) / fade)
    p_out = vb.clamp01((t - leave) / fade)
    return (1 - (1 - p_in) ** 3) * (1 - p_out ** 2)


def draw_tooltip(cv, text, x, y, alpha=1.0, font=None, color=demo.INK, ink=demo.BG, gap=12, rise=8, pad=(11, 6)):
    """A rounded label with a nub pointing down at (x, y), sitting `gap` above
    it. At `alpha` below 1 it also drops by up to `rise` px, so it lifts as it
    fades in. Returns the label's Box."""
    if alpha <= 0:
        return None
    f = font or demo.font(18, 700)
    tw, th = vb.text.block_size([text], f)
    w, h = tw + 2 * pad[0], th + 2 * pad[1]
    nub = 6
    bx, by = x - w / 2, y - gap - nub - h + rise * (1 - alpha)
    with cv.layer(opacity=alpha):
        cv.shadow(bx, by, w, h, radius=7, dy=4, blur=10, color=(0, 0, 0, 0.4))
        cv.rect(bx, by, w, h, color, radius=7)
        ctx = cv.ctx
        ctx.new_path()
        ctx.move_to(x - nub, by + h - 0.5)
        ctx.line_to(x + nub, by + h - 0.5)
        ctx.line_to(x, by + h + nub)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(color))
        ctx.fill()
        vb.text.draw(cv, [text], f, bx + pad[0], by + pad[1], ink)
    box = vb.Box(bx, by, w, h)
    cv.mark('tooltip', *box)
    return box


def tooltip_fade_follow(cv, text, path, t, enter, leave, lag=0.12, fade=0.25, fps=30, **kw):
    """The whole move: the tooltip for `text` trails `path(t) -> (x, y)` by
    `lag` seconds and is shown from `enter` to `leave` seconds, fading at
    each end. `kw` goes to `draw_tooltip`. Returns its Box, or None when hidden."""
    a = hover(t, enter, leave, fade)
    if a <= 0:
        return None
    x, y = follow(path, t, lag, fps)
    return draw_tooltip(cv, text, x, y, alpha=a, **kw)


# The demo: a pointer glides across a small line chart; over the plot the
# tooltip fades in, trails it reading the value underneath, and fades away
# once the pointer moves off.
PX, PY, PW, PH = 170, 160, 620, 240  # the chart panel


def _value(u):
    return 0.5 + 0.28 * math.sin(u * 5.2 + 0.6) + 0.12 * math.sin(u * 13.0)


def _point(u):
    return PX + 30 + (PW - 60) * u, PY + PH - 30 - (PH - 90) * _value(u)


def _u(t):
    """The pointer's place along the chart: off left, across, off right."""
    return vb.interpolate(t, [0.15, 0.6, 2.35, 2.8], [-0.2, 0.0, 1.0, 1.25], ease=vb.ease_in_out_quart) \
        if t < 0.6 or t > 2.35 else (t - 0.6) / 1.75


def _pointer(t):
    u = _u(t)
    x = PX + 30 + (PW - 60) * u
    return x, _point(min(max(u, 0.0), 1.0))[1] + (0 if 0 <= u <= 1 else 20)


def draw(n, cv):
    t = n / demo.FPS
    cv.rect(PX, PY, PW, PH, '#1f242d', radius=14)
    cv.outline(PX, PY, PW, PH, demo.LINE, width=1, radius=14)
    pts = [_point(i / 120) for i in range(121)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, demo.TEAL, width=3)
    cx, cy = _pointer(t)
    u = _u(t)
    on = 0.0 <= u <= 1.0
    if on:
        cv.line(cx, PY + 16, cx, PY + PH - 16, demo.MUTED, width=1, alpha=0.5)
        demo.dot(cv, cx, cy, r=6, color=demo.ACCENT)
    value = round(40 + 60 * _value(min(max(u, 0.0), 1.0)))
    tooltip_fade_follow(cv, f'{value} visits', _pointer, t, enter=0.6, leave=2.35, lag=0.1)
    pts = [(cx + 3 + px * 0.8, cy + 3 + py * 0.8) for px, py in ARROW]
    cv.shape_shadow(pts, dx=1, dy=2, blur=3, color=(0, 0, 0, 0.45))
    ctx = cv.ctx
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(demo.INK))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(demo.BG))
    ctx.set_line_width(1.2)
    ctx.stroke()
    cv.mark('pointer', cx, cy, 18, 27)


TECHNIQUE = Technique(
    id='tooltip-fade-follow',
    name='Tooltip fade follow',
    family='ui',
    group='Overlays & menus',
    aliases=('hover tooltip', 'follow-cursor tooltip', 'cursor tooltip', 'trailing tooltip'),
    definition='A small label fades in once the pointer is over something, drifts along a moment behind '
               'the pointer as it moves, and fades away when the pointer leaves.',
    phrasings=('a tooltip that pops up on hover and tags along with the mouse',
               'show the value in a little bubble that chases the cursor across the chart',
               'a hover label that fades in, follows the pointer, then fades out'),
    related=('range-slider-value-bubble', 'fade-up-scroll-reveal', 'arrow-slide', 'image-hover-mask-reveal',
             'highlighter-swipe', 'per-line-fade-in'),
    api=('videobuilder.techniques.ui.tooltip_fade_follow.tooltip_fade_follow',
         'videobuilder.techniques.ui.tooltip_fade_follow.follow',
         'videobuilder.techniques.ui.tooltip_fade_follow.hover',
         'videobuilder.techniques.ui.tooltip_fade_follow.draw_tooltip'),
    demo=lambda: demo.film(draw),
)

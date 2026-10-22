"""Y2K chrome: any silhouette -- a word, a star, a logo -- turned into the
glossy, cool-blue liquid metal of turn-of-the-millennium graphics: a pale
sky and a hard indigo horizon reflected in the face, the horizon rippling
like liquid, a bevelled rim lit from the top left, a dark extruded edge,
and four-point sparkles that wink on the highlights."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SKY = ('#f6f8ff', '#bccaf4', '#6676c4')          # top of the face down to the horizon
GROUND = ('#0d0f33', '#262a72', '#9ba7ec', '#f2f4ff')  # under the horizon down to the foot
RIM_LIGHT, RIM_DARK, EDGE = '#ffffff', '#141634', '#05060f'


def text_silhouette(text, font, x, y):
    """A silhouette for `y2k_chrome`: `text` on one line (or a list of lines)
    from its top-left (x, y). Returns `(silhouette, box)`."""
    lines = [text] if isinstance(text, str) else list(text)
    w, h = vb.text.block_size(lines, font)

    def silhouette(cv, dx, dy, color):
        vb.text.draw(cv, lines, font, x + dx, y + dy, color)
    return silhouette, vb.Box(x, y, w, h)


def polygon_silhouette(points):
    """A silhouette for `y2k_chrome`: the filled polygon through `points`.
    Returns `(silhouette, box)`."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]

    def silhouette(cv, dx, dy, color):
        ctx = cv.ctx
        ctx.move_to(points[0][0] + dx, points[0][1] + dy)
        for px, py in points[1:]:
            ctx.line_to(px + dx, py + dy)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(color))
        ctx.fill()
    return silhouette, vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def sparkle_points(cx, cy, r, waist=0.16, turn=0.0):
    """The outline of a four-point Y2K sparkle star of radius `r`, its arms
    pinched to `waist` of the radius, rotated by `turn` radians."""
    pts = []
    for i in range(8):
        a = turn + i * math.pi / 4 - math.pi / 2
        k = r if i % 2 == 0 else r * waist
        pts.append((cx + k * math.cos(a), cy + k * math.sin(a)))
    return pts


def _face(ctx, box, t, horizon, wave, glint):
    """Paint the chrome face over `box`: sky gradient, a rippling horizon with
    the ground below it, liquid highlight streaks and an optional glint."""
    x, y, w, h = box.x, box.y, box.w, box.h
    hy = y + h * horizon
    sky = cairo.LinearGradient(0, y, 0, hy)
    for s, c in zip((0.0, 0.55, 1.0), SKY):
        sky.add_color_stop_rgba(s, *vb.rgba(c))
    ctx.set_source(sky)
    ctx.paint()

    def wavy(base, amp, k, speed, phase=0.0):
        steps = 48
        return [(x - 10 + (w + 20) * i / steps,
                 base + amp * math.sin(k * (w + 20) * i / steps / w * 2 * math.pi + speed * t + phase))
                for i in range(steps + 1)]

    amp = h * 0.05 * wave
    edge = wavy(hy, amp, 1.3, 2.4)
    ground = cairo.LinearGradient(0, hy - amp, 0, y + h)
    for s, c in zip((0.0, 0.4, 0.8, 1.0), GROUND):
        ground.add_color_stop_rgba(s, *vb.rgba(c))
    ctx.move_to(*edge[0])
    for p in edge[1:]:
        ctx.line_to(*p)
    ctx.line_to(x + w + 10, y + h + 10)
    ctx.line_to(x - 10, y + h + 10)
    ctx.close_path()
    ctx.set_source(ground)
    ctx.fill()

    # liquid streaks: thin bright ripples in the ground, a soft one in the sky
    for base, k, speed, phase, width, alpha in ((hy + h * 0.16, 2.1, -3.0, 1.0, h * 0.025, 0.55),
                                                (hy + h * 0.28, 1.6, 2.2, 2.5, h * 0.018, 0.45),
                                                (y + h * 0.22, 1.1, 1.5, 0.3, h * 0.03, 0.5)):
        pts = wavy(base, amp * 0.8, k, speed, phase)
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(1, 1, 1, alpha)
        ctx.set_line_width(width)
        ctx.stroke()

    if glint is not None and 0 < glint < 1:
        lean = h * 0.6
        gx = x - lean - w * 0.15 + (w + lean + w * 0.3) * glint
        g = cairo.LinearGradient(gx - w * 0.08, y + h, gx + w * 0.08 + lean, y)
        g.add_color_stop_rgba(0.0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 1, 1, 1, 0.85)
        g.add_color_stop_rgba(1.0, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.paint()


def _rim(cv, silhouette, dx, dy, color, alpha):
    """The silhouette minus itself shifted by (dx, dy): a thin bevel edge on
    the side facing away from the shift, painted in `color`."""
    ctx = cv.ctx
    ctx.push_group()
    silhouette(cv, 0, 0, color)
    ctx.set_operator(cairo.OPERATOR_DEST_OUT)
    silhouette(cv, dx, dy, '#ffffff')
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)


def y2k_chrome(cv, silhouette, box, t, horizon=0.52, wave=1.0, depth=None, bevel=None, glint=None):
    """Draw a silhouette as Y2K liquid chrome. `silhouette(cv, dx, dy, color)`
    draws the shape offset by (dx, dy) in a flat `color` (see
    `text_silhouette`, `polygon_silhouette`); `box` is its bounds. `t` is time
    in seconds and drives the liquid ripple of the reflected horizon, which
    sits at `horizon` of the box height and ripples by `wave` (0 = still
    glass). `depth` is the dark extrusion under the face and `bevel` the lit
    rim width, both in px (default from the box size). `glint`, if given,
    is the 0 -> 1 progress of a white streak across the face."""
    ctx = cv.ctx
    size = min(box.w, box.h)
    depth = size * 0.05 if depth is None else depth
    bevel = max(1.0, size * 0.018) if bevel is None else bevel
    # extruded edge: a stack of dark copies down and to the right, with a black outline
    for ox, oy in ((-1.5, 0), (1.5, 0), (0, -1.5)):
        silhouette(cv, ox, oy, EDGE)
    steps = max(1, round(depth))
    for i in range(steps, 0, -1):
        k = i / steps
        silhouette(cv, depth * 0.35 * k, depth * k, EDGE if i == steps else '#2a2f6e')
    ctx.push_group()
    silhouette(cv, 0, 0, '#ffffff')
    mask = ctx.pop_group()
    ctx.push_group()
    _face(ctx, box, t, horizon, wave, glint)
    ctx.pop_group_to_source()
    ctx.mask(mask)
    _rim(cv, silhouette, bevel, bevel, RIM_LIGHT, 0.9)
    _rim(cv, silhouette, -bevel, -bevel, RIM_DARK, 0.7)


def sparkle(cv, cx, cy, r, alpha=1.0, turn=0.0):
    """A white four-point sparkle with a soft blue halo, the glint Y2K chrome
    wears on its highlights. Animate `r` and `alpha` to make it wink."""
    if r <= 0 or alpha <= 0:
        return
    ctx = cv.ctx
    halo = cairo.RadialGradient(cx, cy, 0, cx, cy, r * 0.9)
    halo.add_color_stop_rgba(0, 0.75, 0.82, 1, 0.7 * alpha)
    halo.add_color_stop_rgba(1, 0.75, 0.82, 1, 0)
    ctx.set_source(halo)
    ctx.arc(cx, cy, r * 0.9, 0, 2 * math.pi)
    ctx.fill()
    pts = sparkle_points(cx, cy, r, waist=0.1, turn=turn)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.fill()


def _backdrop(cv):
    g = cairo.RadialGradient(demo.W / 2, demo.H * 0.55, 0, demo.W / 2, demo.H * 0.55, demo.W * 0.6)
    g.add_color_stop_rgba(0, *vb.rgba('#232a5c'))
    g.add_color_stop_rgba(1, *vb.rgba('#07080f'))
    cv.ctx.set_source(g)
    cv.ctx.paint()


def draw(n, cv):
    t = n / demo.FPS
    _backdrop(cv)
    rise = vb.ease_out_back(demo.phase(n, 0.0, 0.8))
    f = demo.font(210, 900)
    text = 'Y2K'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2 - 80, (demo.H - h) / 2 + 40 * (1 - rise)
    shape, box = text_silhouette(text, f, x, y)
    with cv.layer(opacity=demo.phase(n, 0.0, 0.4)):
        y2k_chrome(cv, shape, box, t, glint=demo.phase(n, 1.0, 2.2))
    star_r = 72 * rise
    sx, sy = box.x + box.w + 105, demo.H / 2 - 20
    if star_r > 1:
        star, sbox = polygon_silhouette(sparkle_points(sx, sy, star_r, waist=0.3, turn=0.25 * math.sin(t * 1.4)))
        y2k_chrome(cv, star, sbox, t + 0.7, horizon=0.5, depth=6, bevel=2.5)
    for at, px, py, size in ((1.2, box.x + box.w * 0.18, box.y + box.h * 0.28, 30),
                             (1.7, box.x + box.w * 0.82, box.y + box.h * 0.66, 24),
                             (2.2, sx + 40, sy - 60, 22)):
        wink = math.sin(math.pi * vb.clamp01((t - at) / 0.6))
        sparkle(cv, px, py, size * wink, alpha=wink, turn=0.6 * (t - at))
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='y2k-chrome',
    name='Y2K chrome',
    family='vfx',
    group='Retro digital',
    aliases=('liquid chrome', 'chrome bubble', 'reflective chrome', 'millennium chrome'),
    definition='Type and shapes become glossy, cool-blue liquid metal, with a pale sky and a dark rippling '
               'horizon reflected in the face, a lit bevel, a dark extruded edge and winking star sparkles.',
    phrasings=('make the logo look like shiny late-90s chrome',
               'give the title that blue liquid-metal Y2K look',
               'turn this shape into glossy reflective chrome with a sparkle on it'),
    related=('chrome-specular-shimmer', 'chrome-reflection', 'gooch-shading', 'thin-film-iridescence',
             'text-reflection-shimmer', 'heat-haze'),
    api=('videobuilder.capabilities.vfx.y2k_chrome.y2k_chrome',
         'videobuilder.capabilities.vfx.y2k_chrome.text_silhouette',
         'videobuilder.capabilities.vfx.y2k_chrome.polygon_silhouette',
         'videobuilder.capabilities.vfx.y2k_chrome.sparkle_points',
         'videobuilder.capabilities.vfx.y2k_chrome.sparkle'),
    demo=lambda: demo.film(draw),
)

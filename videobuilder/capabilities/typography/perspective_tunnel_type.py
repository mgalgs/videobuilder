"""Perspective tunnel type: a word repeated along the four walls of a box
tunnel that runs straight away from the camera, all of it streaming towards
the viewer so it feels like flying down a corridor lined with letters.

The letters are real glyph outlines (title_extruded_3d's `_outline`), laid
on each wall plane and projected through a pinhole at the frame's centre,
so they foreshorten properly rather than just shrinking. Depth fog is one
radial gradient per frame: ink near the edges fading into the background at
the vanishing point.
"""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...compendium.components.title_extruded_3d import _outline

NEAR = 0.2   # the camera's near plane, in tunnel half-heights: glyphs are cut off where they cross it

# The four walls: outward normal (x, y) and which way the text reads along depth
# (+1 away from the camera, -1 towards it), chosen so every wall reads left to right
# or bottom to top on screen.
WALLS = {'floor': ((0, 1), 1), 'right': ((1, 0), -1), 'ceiling': ((0, -1), 1), 'left': ((-1, 0), 1)}


def _clip_near(pts):
    """The closed polygon `pts` of (x, y, z) cut to the part at z >= NEAR."""
    out = []
    for i, cur in enumerate(pts):
        prev = pts[i - 1]
        if (cur[2] >= NEAR) != (prev[2] >= NEAR):
            t = (NEAR - prev[2]) / (cur[2] - prev[2])
            out.append(tuple(a + (b - a) * t for a, b in zip(prev, cur)))
        if cur[2] >= NEAR:
            out.append(cur)
    return out


def _wall_frame(normal, along, half_w, half_h):
    """(origin, across) of a wall: the point on its centre line in the xy plane and
    the in-wall unit vector the text's up (-v) points along, picked so the glyphs are
    not mirrored on screen."""
    nx, ny = normal
    origin = (nx * half_w, ny * half_h)
    across = (-ny, nx)

    def screen(u, v):
        x = origin[0] - across[0] * v
        y = origin[1] - across[1] * v
        z = 3 + along * u
        return x / z, y / z
    (x0, y0), (x1, y1), (x2, y2) = screen(0, 0), screen(0.1, 0), screen(0, 0.1)
    if (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0) < 0:
        across = (ny, -nx)
    return origin, across


def draw_tunnel_type(cv, text, font, travel, color=demo.INK, fog=demo.BG, walls=tuple(WALLS), cx=None, cy=None,
                     scale=None, aspect=None, height=0.42, leading=1.2, gap=0.5, far=40.0, colors=None,
                     edges=demo.LINE):
    """Draw `text` repeated end to end in rows down the walls of a box tunnel
    seen from inside, the camera `travel` tunnel half-heights along it:
    animate `travel` upward and the words stream towards the viewer.

    The tunnel's mouth fills the frame (`scale`, default half the frame
    height, is its half-height in px at depth 1; `aspect` its width/height,
    default the frame's), centred on the vanishing point (`cx`, `cy`).
    `height` is a row's height as a fraction of the tunnel's half-height,
    rows `leading` heights apart and as many as fit across each wall,
    staggered; `gap` is the space between repeats, in the same unit; `far`
    how deep the walls run. Each wall in `walls` (names from `WALLS`) fills
    with `colors[wall]` if given, else `color`, fading into `fog` towards the
    vanishing point. `edges`, if not None, strokes the tunnel's four corners."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    k = cv.height / 2 if scale is None else scale
    half_h = 1.0
    half_w = (cv.width / cv.height if aspect is None else aspect) * half_h
    contours, (bw, bh) = _outline((text,), font)
    s = height / bh                       # px of outline -> tunnel units
    length = bw * s
    period = length + gap
    count = int(far / period) + 2
    ctx = cv.ctx
    reach = math.hypot(cv.width, cv.height) / 2

    def fogged(ink):
        grad = cairo.RadialGradient(cx, cy, 0, cx, cy, reach)
        grad.add_color_stop_rgba(0.0, *vb.rgba(fog))
        grad.add_color_stop_rgba(0.1, *vb.rgba(fog))
        grad.add_color_stop_rgba(0.8, *vb.rgba(ink))
        return grad

    if edges is not None:
        ctx.new_path()
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ctx.move_to(cx + k * sx * half_w / NEAR, cy + k * sy * half_h / NEAR)
            ctx.line_to(cx + k * sx * half_w / far, cy + k * sy * half_h / far)
        ctx.set_source(fogged(edges))
        ctx.set_line_width(2)
        ctx.stroke()
    for name in walls:
        normal, along = WALLS[name]
        (ox, oy), (ax, ay) = _wall_frame(normal, along, half_w, half_h)
        span = 2 * (half_h if normal[0] else half_w)       # the wall's width across the text
        rows = max(1, int(span / (height * leading)))
        ctx.new_path()
        for r in range(rows):
            off = (r - (rows - 1) / 2) * height * leading   # row centre, across the wall
            shift = (travel + r * period * 0.38) % period
            for i in range(count):
                mid = i * period - shift + length / 2
                if mid + length / 2 < NEAR:
                    continue
                for c in contours:
                    pts = [(ox + ax * (off - v * s), oy + ay * (off - v * s), mid + along * u * s) for u, v in c]
                    pts = _clip_near(pts) if min(p[2] for p in pts) < NEAR else pts
                    for j, (x, y, z) in enumerate(pts):
                        (ctx.move_to if j == 0 else ctx.line_to)(cx + k * x / z, cy + k * y / z)
                    if pts:
                        ctx.close_path()
        ctx.set_source(fogged((colors or {}).get(name, color)))
        ctx.fill()


def draw(n, cv):
    t = n / demo.FPS
    travel = 2.2 * t + 0.6 * t * t      # speeds up a little, like a camera pushing in
    draw_tunnel_type(cv, 'TUNNEL VISION', demo.font(200, 900), travel,
                     colors={'floor': demo.INK, 'ceiling': demo.INK, 'left': demo.ACCENT, 'right': demo.TEAL})
    cv.mark('text', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='perspective-tunnel-type',
    name='Perspective tunnel type',
    family='typography',
    group='Depth and 3D',
    aliases=('tunnel text', 'text tunnel', 'typographic tunnel', 'corridor type'),
    definition='Words line the walls of a corridor that recedes to a vanishing point, sliding towards '
               'the camera so it feels like flying through a tunnel made of type.',
    phrasings=('fly down a tunnel whose walls are covered in the words',
               'text on all four sides of a corridor rushing past the camera',
               'the title repeated on the walls, floor and ceiling of a 3D tunnel'),
    related=('perspective-crawl', 'scale-zoom-through', 'texture-tunnel', 'word-flip-in', 'zoom-through-shape',
             'infinite-zoom-tunnel'),
    api=('videobuilder.techniques.typography.perspective_tunnel_type.draw_tunnel_type',),
    demo=lambda: demo.film(draw),
)

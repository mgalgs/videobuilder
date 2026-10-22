"""Globe Spin: a shaded sphere carrying a coarse world map turns steadily
about its own north-south axis, continents sliding in over one edge and out
over the other, the way a news open or a travel graphic shows "the world".

The globe is drawn as vectors: each land outline is a ring of (longitude,
latitude) points, projected orthographically and clipped at the horizon, the
hidden stretch of a ring replaced by an arc of the globe's rim."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

# Coarse land outlines as (longitude, latitude) rings in degrees: enough to
# read as the familiar world at a glance, not a real coastline.
LAND = (
    # Africa
    ((-17, 21), (-10, 30), (-6, 36), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (51, 12), (42, -1),
     (40, -10), (35, -24), (27, -34), (18, -34), (12, -17), (9, -1), (5, 5), (-8, 5), (-17, 14)),
    # Eurasia
    ((-9, 37), (-9, 43), (-1, 46), (-4, 48), (5, 53), (8, 57), (5, 61), (15, 69), (28, 71), (40, 67), (60, 69),
     (70, 73), (90, 76), (110, 77), (140, 72), (160, 70), (180, 67), (175, 62), (162, 58), (156, 51), (140, 53),
     (135, 43), (129, 35), (122, 31), (117, 23), (108, 21), (106, 10), (100, 13), (103, 2), (98, 8), (97, 16),
     (91, 22), (80, 15), (77, 8), (73, 20), (67, 24), (57, 25), (59, 22), (53, 16), (43, 12), (39, 21),
     (34, 29), (34, 32), (36, 36), (26, 40), (23, 37), (19, 41), (13, 45), (16, 40), (10, 44), (3, 43),
     (-1, 37)),
    # North America
    ((-168, 66), (-160, 71), (-140, 70), (-125, 70), (-95, 72), (-80, 70), (-65, 60), (-60, 53), (-56, 48),
     (-66, 45), (-70, 41), (-76, 35), (-81, 31), (-80, 26), (-83, 29), (-90, 30), (-97, 27), (-97, 21),
     (-90, 21), (-87, 15), (-83, 9), (-78, 8), (-85, 11), (-92, 15), (-105, 20), (-110, 23), (-112, 31),
     (-115, 30), (-118, 34), (-124, 40), (-124, 48), (-135, 58), (-150, 60), (-165, 55), (-160, 59),
     (-166, 62)),
    # South America
    ((-78, 8), (-72, 12), (-62, 11), (-50, 2), (-35, -6), (-39, -16), (-48, -26), (-58, -38), (-65, -42),
     (-68, -52), (-72, -53), (-74, -45), (-73, -36), (-71, -18), (-76, -14), (-81, -5), (-80, 0)),
    # Australia
    ((114, -22), (122, -17), (130, -12), (137, -12), (137, -16), (142, -11), (146, -19), (153, -26),
     (150, -37), (141, -38), (135, -34), (130, -31), (116, -35), (114, -26)),
    # Greenland
    ((-55, 60), (-45, 60), (-20, 70), (-20, 80), (-35, 83), (-60, 82), (-72, 78), (-55, 70)),
    # Britain, Japan, Borneo, Madagascar
    ((-5, 50), (1, 51), (0, 53), (-3, 58), (-6, 57), (-5, 54)),
    ((130, 31), (140, 35), (142, 40), (141, 45), (139, 40), (132, 34)),
    ((109, 1), (117, 7), (119, 1), (116, -4), (110, -3)),
    ((44, -25), (47, -25), (50, -15), (49, -12), (44, -17)),
)


def globe_point(lon, lat, spin, tilt):
    """Unit-sphere point at (`lon`, `lat`) degrees, seen with longitude
    `spin` radians at the centre and the view `tilt` radians above the
    equator: (x right, y up, z toward the viewer). Visible when z > 0."""
    lam, phi = math.radians(lon) - spin, math.radians(lat)
    cl = math.cos(phi)
    x = cl * math.sin(lam)
    y = math.cos(tilt) * math.sin(phi) - math.sin(tilt) * cl * math.cos(lam)
    z = math.sin(tilt) * math.sin(phi) + math.cos(tilt) * cl * math.cos(lam)
    return x, y, z


def _dense(ring, step=3.0, closed=True):
    """`ring` with extra points so no edge is longer than `step` degrees."""
    out = []
    pts = list(ring) + ([ring[0]] if closed else [])
    for (a, b), (c, d) in zip(pts, pts[1:]):
        k = max(1, int(math.hypot(c - a, d - b) / step))
        out += [(a + (c - a) * i / k, b + (d - b) * i / k) for i in range(k)]
    if not closed:
        out.append(pts[-1])
    return out


def _horizon(p, q):
    """Where the edge p -> q (sphere points either side of z = 0) meets the rim."""
    t = p[2] / (p[2] - q[2])
    x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
    return math.atan2(y, x)


def _land_path(ctx, ring, spin, tilt, cx, cy, r):
    """Add the visible part of one land ring to `ctx`'s path. Returns False
    when the ring is wholly behind the globe."""
    pts = [globe_point(lon, lat, spin, tilt) for lon, lat in _dense(ring)]
    if not any(p[2] > 0 for p in pts):
        return False
    if all(p[2] > 0 for p in pts):
        ctx.move_to(cx + r * pts[0][0], cy - r * pts[0][1])
        for x, y, _ in pts[1:]:
            ctx.line_to(cx + r * x, cy - r * y)
        ctx.close_path()
        return True
    # start on a hidden point, so the walk opens with a crossing into view
    k = next(i for i, p in enumerate(pts) if p[2] <= 0)
    pts = pts[k:] + pts[:k]
    n = len(pts)

    def turn(a, b):
        return (b - a + math.pi) % (2 * math.pi) - math.pi

    # a hidden stretch becomes a rim arc turning as far as its points, pushed
    # out to the rim, turn: that keeps the arc on the correct side of the globe
    prev, sweep, exit_at, entry_at, lead = math.atan2(pts[0][1], pts[0][0]), 0.0, None, None, 0.0
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        if p[2] <= 0 < q[2]:  # into view
            a = _horizon(p, q)
            sweep += turn(prev, a)
            if entry_at is None:
                entry_at, lead = a, sweep
                ctx.move_to(cx + r * math.cos(a), cy - r * math.sin(a))
            else:
                _rim(ctx, exit_at, sweep, cx, cy, r)
            ctx.line_to(cx + r * q[0], cy - r * q[1])
        elif p[2] > 0 and q[2] > 0:
            ctx.line_to(cx + r * q[0], cy - r * q[1])
        elif p[2] > 0 >= q[2]:  # out of view
            exit_at = prev = _horizon(p, q)
            sweep = 0.0
            ctx.line_to(cx + r * math.cos(exit_at), cy - r * math.sin(exit_at))
        if q[2] <= 0 and i + 1 < n:
            a = math.atan2(q[1], q[0])
            sweep += turn(prev, a)
            prev = a
    # the last hidden stretch runs on through the start to the first entry
    sweep += turn(prev, math.atan2(pts[0][1], pts[0][0])) + lead
    _rim(ctx, exit_at, sweep, cx, cy, r)
    ctx.close_path()
    return True


def _rim(ctx, a0, sweep, cx, cy, r):
    """Path along the rim from angle `a0` (maths convention, y up) through `sweep` radians."""
    steps = max(1, int(abs(sweep) / 0.05))
    for i in range(1, steps + 1):
        a = a0 + sweep * i / steps
        ctx.line_to(cx + r * math.cos(a), cy - r * math.sin(a))


def globe(cv, cx, cy, r, spin, tilt=math.radians(18), ocean='#1d2f4f', land='#b9c8ef', grid=True,
          land_rings=LAND, shade=True):
    """Draw a globe of radius `r` centred at (cx, cy), turned so longitude
    `spin` radians east faces the viewer (raise it over time and the map
    slides right to left; lower it for the other way), the view `tilt` radians above the
    equator. `land_rings` are (lon, lat) degree rings filled in `land` over an
    `ocean` disc; `grid` adds faint meridians and parallels, `shade` a soft
    light from the upper left. Returns the globe's Box."""
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*vb.rgba(ocean))
    ctx.fill_preserve()
    ctx.clip()
    ctx.set_source_rgba(*vb.rgba(land))
    for ring in land_rings:  # one fill each, so overlapping rings never cancel out
        ctx.new_path()
        if _land_path(ctx, ring, spin, tilt, cx, cy, r):
            ctx.fill()
    ctx.new_path()
    if grid:
        lines = [[(lon, lat) for lat in range(-90, 91, 3)] for lon in range(0, 360, 30)]
        lines += [[(lon, lat) for lon in range(-180, 181, 3)] for lat in range(-60, 61, 30)]
        for line in lines:
            prev = None
            for lon, lat in line:
                x, y, z = globe_point(lon, lat, spin, tilt)
                if z > 0:
                    if prev:
                        ctx.line_to(cx + r * x, cy - r * y)
                    else:
                        ctx.move_to(cx + r * x, cy - r * y)
                prev = z > 0
        ctx.set_source_rgba(*vb.rgba(kit.mix(ocean, '#ffffff', 0.35), 0.35))
        ctx.set_line_width(max(1.0, r * 0.006))
        ctx.stroke()
    if shade:
        g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.05, cx - r * 0.1, cy - r * 0.1, r * 1.15)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.22)
        g.add_color_stop_rgba(0.45, 1, 1, 1, 0.0)
        g.add_color_stop_rgba(0.8, 0, 0, 0, 0.25)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.6)
        ctx.set_source(g)
        ctx.paint()
    ctx.restore()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*vb.rgba(land, 0.25))
    ctx.set_line_width(max(1.0, r * 0.008))
    ctx.stroke()
    return vb.Box(cx - r, cy - r, 2 * r, 2 * r)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 12, demo.H * 0.36
    # a soft contact shadow, still, so only the globe's surface moves
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, cy + r * 1.12)
    ctx.scale(1, 0.12)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, r * 0.9)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.5)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, r * 0.9, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()
    spin = math.radians(-20 + 120 * n / demo.FPS)  # a steady third of a turn a second
    box = globe(cv, cx, cy, r, spin, land=kit.mix(demo.TEAL, '#ffffff', 0.25))
    cv.mark('globe', *box)


CAPABILITY = Capability(
    id='globe-spin',
    name='Globe spin',
    family='broadcast',
    group='Maps',
    aliases=('globe rotation', 'rotating globe', 'spinning earth'),
    definition='A shaded ball printed with a world map turns at a steady pace about its north-south axis, '
               'so continents keep rolling into view on one side and away on the other.',
    phrasings=('show the earth slowly spinning',
               'put a rotating globe behind the world news title',
               'make a 3D world map turn round and round'),
    related=('turntable-rotation', 'spin', 'tesseract-rotation', 'isometric-rotation', 'cube-rotate', 'swirl'),
    api=('videobuilder.capabilities.broadcast.globe_spin.globe',
         'videobuilder.capabilities.broadcast.globe_spin.globe_point',
         'videobuilder.capabilities.broadcast.globe_spin.LAND'),
    demo=lambda: demo.film(draw),
)

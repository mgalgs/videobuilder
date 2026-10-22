"""Flight arc: a curved route line that lifts off one map point and draws
itself across to another, the way news and travel graphics show a flight or
a long-distance link."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def flight_arc(a, b, lift=0.3, n=64):
    """The route from point `a` to point `b` (film px) as an `n`-point list:
    a quadratic curve bowed upward (towards smaller y) by `lift` times the
    distance between them, so longer hops arc higher."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1.0
    nx, ny = dy / d, -dx / d          # a normal to the chord; flip it so it points up the frame
    if ny > 0:
        nx, ny = -nx, -ny
    cx, cy = (x0 + x1) / 2 + nx * lift * d, (y0 + y1) / 2 + ny * lift * d
    out = []
    for i in range(n):
        t = i / (n - 1)
        u = 1 - t
        out.append((u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1))
    return out


def draw_flight_arc(cv, a, b, progress, color=demo.ACCENT, width=3, lift=0.3, head=True, alpha=1.0):
    """Draw the leading `progress` (0..1) of the flight arc from `a` to `b`,
    with an arrowhead riding its tip while it is still travelling. Returns
    the tip's (x, y)."""
    pts = vb.paths.reveal(flight_arc(a, b, lift), progress)
    if len(pts) < 2:
        return a
    vb.paths.draw(cv, pts, color, width=width, alpha=alpha)
    (px, py), (x, y) = pts[-2], pts[-1]
    if head and progress < 1:
        ang = math.atan2(y - py, x - px)
        s = width * 4
        c = cv.ctx
        c.new_path()
        c.move_to(x + math.cos(ang) * s, y + math.sin(ang) * s)
        c.line_to(x + math.cos(ang + 2.5) * s, y + math.sin(ang + 2.5) * s)
        c.line_to(x + math.cos(ang - 2.5) * s, y + math.sin(ang - 2.5) * s)
        c.close_path()
        c.set_source_rgba(*vb.canvas.rgba(color, alpha))
        c.fill()
    return x, y


# Low-poly continents as (longitude, latitude) outlines, for the demo map.
_LAND = (
    ((-165, 64), (-140, 70), (-95, 72), (-75, 62), (-58, 50), (-70, 42), (-81, 25), (-97, 18),
     (-106, 22), (-124, 40), (-133, 56), (-160, 58)),
    ((-55, 82), (-22, 81), (-20, 70), (-44, 60), (-56, 74)),
    ((-80, 10), (-60, 9), (-35, -6), (-40, -22), (-66, -55), (-74, -44), (-81, -5)),
    ((-10, 36), (-9, 55), (10, 70), (40, 70), (80, 75), (140, 72), (178, 66), (160, 58), (142, 42),
     (122, 30), (108, 18), (100, 3), (90, 22), (78, 8), (70, 22), (56, 25), (42, 14), (34, 31),
     (25, 37), (10, 38)),
    ((-17, 21), (-8, 35), (10, 37), (32, 31), (43, 12), (51, 12), (40, -15), (20, -35), (12, -18),
     (9, 4), (-8, 5)),
    ((114, -22), (130, -12), (142, -11), (153, -27), (146, -39), (132, -32), (115, -34)),
)
_MAP = (90, 60, 870, 470)          # the map's box in the frame: x0, y0, x1, y1
_LON, _LAT = (-170, 180), (82, -58)


def _to_frame(lon, lat):
    x0, y0, x1, y1 = _MAP
    return (x0 + (lon - _LON[0]) / (_LON[1] - _LON[0]) * (x1 - x0),
            y0 + (lat - _LAT[0]) / (_LAT[1] - _LAT[0]) * (y1 - y0))


def _map(cv):
    x0, y0, x1, y1 = _MAP
    for lon in range(-150, 181, 30):
        x, _ = _to_frame(lon, 0)
        cv.line(x, y0, x, y1, demo.LINE, width=1)
    for lat in range(-45, 81, 25):
        _, y = _to_frame(0, lat)
        cv.line(x0, y, x1, y, demo.LINE, width=1)
    for shape in _LAND:
        vb.paths.draw(cv, [_to_frame(*p) for p in shape], '#2e3442', fill=True)


def draw(n, cv):
    a, b = _to_frame(-74, 41), _to_frame(139, 36)      # New York -> Tokyo
    _map(cv)
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 2.2))
    draw_flight_arc(cv, a, b, p)
    cv.mark('arc', min(a[0], b[0]), 0, abs(b[0] - a[0]), demo.H)
    pulse = demo.phase(n, 0.0, 0.6)
    demo.dot(cv, *a, r=7 * vb.ease_out_back(pulse))
    land = demo.phase(n, 2.2, 2.9)
    if 0 < land < 1:
        cv.arc(*b, 7 + 26 * land, 0, 2 * math.pi, demo.ACCENT, width=2, alpha=1 - land)
    demo.dot(cv, *b, r=7, color=demo.ACCENT if land > 0 else demo.INK)


TECHNIQUE = Technique(
    id='flight-arc',
    name='Flight arc',
    family='broadcast',
    group='Maps',
    aliases=('great-circle arc', 'curved route arc', 'route arc'),
    definition='A bowed line climbs out of one point on a map and draws itself over to another, '
               'tracing a flight path or long-distance link between the two places.',
    phrasings=('draw a curved flight path between two cities on the map',
               'show a plane route arcing from New York to Tokyo',
               'animate a connection line that arches across the world map'),
    related=('projectile-arc', 'arcs', 'arc-bend-morph', 'bend-deformer', 'electric-arc', 'chord-diagram-draw'),
    api=('videobuilder.techniques.broadcast.flight_arc.flight_arc',
         'videobuilder.techniques.broadcast.flight_arc.draw_flight_arc'),
    demo=lambda: demo.film(draw),
)

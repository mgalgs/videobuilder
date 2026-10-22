"""Map Route Draw: a travel line grows across a map from stop to stop, a marker
riding its tip, each stop's pin popping in as the line reaches it."""
import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def route_legs(stops, bow=0.18, steps=32):
    """One point list per leg between consecutive `stops` ((x, y) pairs), each
    a gentle arc bowed sideways by `bow` times the leg's length (0: straight;
    the sign flips which side), the way flight paths are drawn on a flat map."""
    legs = []
    for (x0, y0), (x1, y1) in zip(stops, stops[1:]):
        dx, dy = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2 + dy * bow, (y0 + y1) / 2 - dx * bow
        legs.append([((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
                      (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
                     for t in (i / steps for i in range(steps + 1))])
    return legs


def stop_fractions(stops, bow=0.18):
    """Where each stop sits along the whole route, 0 -> 1 by length: the
    `progress` at which `draw_route`'s line reaches it, for cueing labels."""
    lengths = [paths.length(leg) for leg in route_legs(stops, bow)]
    total = sum(lengths) or 1.0
    out, at = [0.0], 0.0
    for d in lengths:
        at += d
        out.append(at / total)
    return out


def _pin(cv, x, y, s, color, ring):
    """A stop marker scaled by `s` (0 -> 1, may overshoot): a ring with a dot."""
    if s <= 0:
        return
    demo.dot(cv, x, y, 13 * s, color=ring)
    demo.dot(cv, x, y, 8 * s, color=color)


def draw_route(cv, stops, progress, color=demo.ACCENT, width=6, bow=0.18, ghost=demo.MUTED,
               ring=demo.INK, marker=True):
    """Draw the route through `stops` grown to `progress` (0 -> 1 along its
    whole length): the full path faint and dashed underneath (`ghost`, None
    for none), the travelled part solid in `color`, a pin at every stop
    reached (popping in with a small overshoot) and, while travelling, a
    marker at the tip. Returns the tip's (x, y)."""
    legs = route_legs(stops, bow)
    whole = [p for i, leg in enumerate(legs) for p in (leg if i == 0 else leg[1:])]
    total = paths.length(whole) or 1.0
    if ghost:
        c = cv.ctx
        c.save()
        c.set_dash([10, 10])
        paths.draw(cv, whole, ghost, width=2, alpha=0.6)
        c.restore()
    progress = vb.clamp01(progress)
    done = paths.reveal(whole, progress)
    paths.draw(cv, done, color, width=width)
    tip = done[-1] if done else stops[0]
    for (x, y), at in zip(stops, stop_fractions(stops, bow)):
        # each pin pops in over the last 60 px of line before it, so the origin is there from the start
        _pin(cv, x, y, vb.ease_out_back(vb.clamp01((progress - at) * total / 60 + 1)), color, ring)
    if marker and 0 < progress < 1:
        demo.dot(cv, tip[0], tip[1], 16, color=ring, alpha=0.25)
        demo.dot(cv, tip[0], tip[1], 9, color=ring)
    return tip


# The demo's map: three landmasses (rough outlines, torn into coastlines)
# under a faint graticule, and a route hopping between four cities.
LAND = (
    [(70, 120), (250, 70), (360, 130), (340, 260), (250, 330), (180, 470), (110, 400), (60, 250)],
    [(430, 90), (640, 60), (700, 180), (610, 250), (520, 300), (440, 230)],
    [(560, 330), (760, 270), (900, 330), (880, 470), (700, 500), (590, 450)],
)
STOPS = [(170, 200), (300, 380), (560, 160), (790, 400)]
NAMES = ('ORIGIN', 'STOP 1', 'STOP 2', 'ARRIVAL')
_COAST = [paths.torn(paths.resample(land, 60, closed=True), seed=i, amount=6) for i, land in enumerate(LAND)]


def _map(cv):
    cv.fill('#182230')
    for x in range(0, demo.W + 1, 80):
        cv.line(x, 0, x, demo.H, '#22303f', width=1)
    for y in range(30, demo.H, 80):
        cv.line(0, y, demo.W, y, '#22303f', width=1)
    for coast in _COAST:
        paths.draw(cv, coast, '#2b3a4c', fill=True)
        paths.draw(cv, coast, '#3b4d63', width=1.5, closed=True)


def draw(n, cv):
    _map(cv)
    p = demo.phase(n, 0.3, 2.5)
    p = p * p * (3 - 2 * p)
    tip = draw_route(cv, STOPS, p)
    f = demo.mono(15, 700)
    for (x, y), name, at in zip(STOPS, NAMES, stop_fractions(STOPS)):
        shown = vb.clamp01((p - at) * 12 + 1)
        if shown > 0:
            w, h = vb.text.block_size([name], f)
            vb.text.draw(cv, [name], f, x - w / 2, y + 20, demo.INK, alpha=shown)
    cv.mark('tip', tip[0] - 9, tip[1] - 9, 18, 18)


CAPABILITY = Capability(
    id='map-route-draw',
    name='Map route draw',
    family='shapes',
    group='Explainer & infographic',
    aliases=('route animation', 'travel path animation', 'journey line', 'flight path map'),
    definition='A line traces a journey across a map, growing from one stop to the next with a marker '
               'at its tip while each place is pinned as the line arrives.',
    phrasings=('show our trip being drawn on the map city by city',
               'animate the route line travelling from start to destination',
               'a path that draws itself across the map with pins at each stop'),
    related=('flow-map-lines', 'stroke-draw-on', 'line-chart-draw-on', 'player-movement-trail',
             'text-on-a-path', 'path-emitter'),
    api=('videobuilder.capabilities.shapes.map_route_draw.draw_route',
         'videobuilder.capabilities.shapes.map_route_draw.route_legs',
         'videobuilder.capabilities.shapes.map_route_draw.stop_fractions',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

"""Isochrone expansion: on a map, the edge of "everywhere you can get to from
here" grows outward as the travel-time budget ticks up. It spreads unevenly,
fast along easy directions and slow along hard ones, and leaves nested
shaded bands behind it at round-number times (15, 30, 45 minutes)."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def travel_speed(base, ripples=((2, 0.22, 0.6), (3, 0.14, -1.1), (5, 0.07, 2.0))):
    """A ready-made `speed(angle)` for `isochrone`: `base` px per minute, swelled
    and pinched by a few smooth waves around the compass, each
    (harmonic, depth, phase). Gives the blobby, lopsided outline a reach map
    has without needing a road network."""
    def speed(angle):
        return base * max(0.15, 1 + sum(d * math.cos(k * angle + ph) for k, d, ph in ripples))
    return speed


def isochrone(cx, cy, minutes, speed, samples=144):
    """The closed outline reachable from (cx, cy) within `minutes`, travelling
    `speed(angle)` px per minute in each direction (angle in radians, 0 = east,
    clockwise on screen). A list of `samples` (x, y) points."""
    out = []
    for i in range(samples):
        a = 2 * math.pi * i / samples
        r = max(0.0, minutes) * speed(a)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def reach_time(cx, cy, speed, x, y):
    """Minutes it takes to get from (cx, cy) to (x, y) under the same `speed`
    as `isochrone`: a point is inside the `isochrone` for `minutes` exactly when
    this is at most `minutes`. Use it to light up places as the edge passes them."""
    d = math.hypot(x - cx, y - cy)
    return d / speed(math.atan2(y - cy, x - cx)) if d else 0.0


def draw_isochrones(cv, cx, cy, minutes, speed, bands=(15, 30, 45), color=demo.TEAL, edge=demo.ACCENT,
                    width=3.0, fill=0.16, label=None):
    """Draw the reach map from (cx, cy) at a travel budget of `minutes`: one
    shaded band per entry in `bands` the budget has passed (inner bands
    stacked brighter, with a thin `color` outline), then the live front at
    `minutes` filled faintly and stroked in `edge`. `label(text, x, y)`, if
    given, is called for each finished band with a point on its rim (to its
    lower right), e.g. to tag it "30 min". Returns the live front's points."""
    done = [b for b in bands if b < minutes]
    front = isochrone(cx, cy, minutes, speed)
    vb.paths.draw(cv, front, color, fill=True, alpha=fill)
    for b in reversed(done):
        vb.paths.draw(cv, isochrone(cx, cy, b, speed), color, fill=True, alpha=fill)
    for b in done:
        ring = isochrone(cx, cy, b, speed)
        vb.paths.draw(cv, ring, color, width=1.5, closed=True, alpha=0.75)
        if label:
            a = math.pi / 5
            r = b * speed(a)
            label(f'{b} min', cx + r * math.cos(a), cy + r * math.sin(a))
    if minutes > 0:
        vb.paths.draw(cv, front, edge, width=width, closed=True)
    return front


# --- demo -------------------------------------------------------------------

M = 24                                   # map inset from the frame
ORIGIN = (420, 285)
SPEED = travel_speed(4.3)
TOTAL = 60                               # minutes reached by the end
PLACES = (('A', 300, 200), ('B', 440, 120), ('C', 560, 180), ('D', 700, 250), ('E', 610, 360),
          ('F', 470, 440), ('G', 330, 380), ('H', 170, 330), ('J', 250, 150))


def _street_x(i, y):
    return M + 30 + i * 58 + 7 * math.sin(y / 70 + i * 1.7)


def _street_y(j, x):
    return M + 26 + j * 52 + 6 * math.sin(x / 90 + j * 2.3)


def _map(cv):
    cv.rect(M, M, demo.W - 2 * M, demo.H - 2 * M, '#1b1d24', radius=16)
    with cv.clip(M, M, demo.W - 2 * M, demo.H - 2 * M, radius=16):
        for i in range(16):
            vb.paths.draw(cv, [(_street_x(i, y), y) for y in range(M, demo.H - M + 1, 12)], demo.LINE, width=5)
        for j in range(10):
            vb.paths.draw(cv, [(x, _street_y(j, x)) for x in range(M, demo.W - M + 1, 12)], demo.LINE, width=5)
        river = [(800 + 40 * math.sin(y / 60), y) for y in range(M, demo.H - M + 1, 8)]
        vb.paths.draw(cv, river, '#2c3a5c', width=22)


def _tag(cv, text, x, y, color=demo.INK, bg='#0f1014', size=15):
    f = kit.font(size, 700)
    w, h = vb.text.block_size([text], f)
    cv.rect(x - 5, y - 3, w + 10, h + 6, bg, radius=5, alpha=0.85)
    vb.text.draw(cv, [text], f, x, y, color)


def draw(n, cv):
    minutes = TOTAL * (1 - (1 - demo.phase(n, 0.2, 2.75)) ** 2)
    cx, cy = ORIGIN
    _map(cv)
    with cv.clip(M, M, demo.W - 2 * M, demo.H - 2 * M, radius=16):
        draw_isochrones(cv, cx, cy, minutes, SPEED, label=lambda t, x, y: _tag(cv, t, x + 4, y + 2, size=13))
    for name, x, y in PLACES:
        t = reach_time(cx, cy, SPEED, x, y)
        lit = vb.clamp01((minutes - t) * 0.6)    # pops over ~1.7 minutes once the edge passes
        demo.dot(cv, x, y, 5 + 3 * vb.ease_out_back(lit), kit.mix(demo.MUTED, demo.ACCENT, lit))
        _tag(cv, f'{name} {round(t)}', x + 10, y - 22, kit.mix(demo.MUTED, demo.INK, lit), size=13)
    demo.dot(cv, cx, cy, 12, demo.INK)
    demo.dot(cv, cx, cy, 7, demo.ACCENT)
    _tag(cv, f'{round(minutes)} min', M + 18, M + 16, demo.ACCENT, size=26)
    _tag(cv, 'TRAVEL TIME', demo.W - M - 120, demo.H - M - 34, demo.MUTED, size=13)
    cv.mark('map', M, M, demo.W - 2 * M, demo.H - 2 * M)


TECHNIQUE = Technique(
    id='isochrone-expansion',
    name='Isochrone expansion',
    family='broadcast',
    group='Maps',
    aliases=('travel-time rings', 'reach ring expansion', 'isochrone map', 'travel-time map'),
    definition='A lopsided outline swells across a map from a starting pin as a minutes counter rises, '
               'swallowing nearby places and leaving shaded bands behind at each round travel time.',
    phrasings=('show how far you can get from this spot in 15, 30 and 60 minutes',
               'animate the area you can reach growing outward on the map over time',
               'a commute-time zone spreading from a location and lighting up places it reaches'),
    related=('offset-path-expansion', 'orbital-pulse', 'radial-stagger', 'circle-packing', 'edge-in-stagger',
             'ripple-rings'),
    api=('videobuilder.techniques.broadcast.isochrone_expansion.draw_isochrones',
         'videobuilder.techniques.broadcast.isochrone_expansion.isochrone',
         'videobuilder.techniques.broadcast.isochrone_expansion.reach_time',
         'videobuilder.techniques.broadcast.isochrone_expansion.travel_speed'),
    demo=lambda: demo.film(draw),
)

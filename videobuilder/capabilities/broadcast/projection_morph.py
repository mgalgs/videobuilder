"""Projection Morph: a spinning globe unrolls into a flat world map (or rolls
back up), every coastline and grid line sliding smoothly from where the
sphere puts it to where the flat map does."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def _bend(progress):
    """How round the projection still is: 1 for the globe, ~0 for the flat map."""
    return max(1.0 - vb.clamp01(progress), 1e-6)


def visible_span(progress):
    """How far either side of the centre meridian (degrees, up to 180) the
    surface shows at `progress`: one hemisphere on the globe, widening as it
    unrolls, the whole world once it is half flat."""
    return min(180.0, 90.0 / _bend(progress))


def projection_morph(lon, lat, progress, radius):
    """Where the point at `lon`, `lat` (degrees; `lon` relative to the centre
    meridian, in -180..180) lands at `progress`, as an (x, y) offset from the
    centre with y down: 0 is an orthographic globe of `radius`, 1 the
    equirectangular map of the same scale (2 pi `radius` wide, pi `radius`
    tall). In between, the sphere's curvature relaxes evenly, so the far side
    swings into view as the surface flattens. Points past `visible_span` are
    on the hidden side; callers skip them."""
    g = _bend(progress)
    lam, phi = math.radians(lon) * g, math.radians(lat) * g
    return radius * math.cos(phi) * math.sin(lam) / g, -radius * math.sin(phi) / g


# A coarse world in (lon, lat) outlines: enough to read as the Earth, rasterised
# into cells once so hidden-side clipping is per cell, not per polygon.
CONTINENTS = (
    [(-165, 65), (-155, 71), (-125, 70), (-95, 72), (-80, 68), (-62, 60), (-55, 50), (-66, 44), (-76, 35),
     (-81, 25), (-90, 29), (-97, 26), (-97, 20), (-87, 16), (-83, 9), (-78, 8), (-92, 15), (-105, 20),
     (-112, 30), (-118, 34), (-124, 40), (-125, 49), (-135, 58), (-150, 60), (-165, 60)],
    [(-55, 60), (-42, 60), (-20, 70), (-18, 80), (-40, 83), (-65, 80), (-58, 70)],
    [(-80, 9), (-72, 12), (-60, 10), (-50, 0), (-35, -5), (-39, -15), (-48, -26), (-58, -38), (-65, -42),
     (-68, -54), (-74, -50), (-72, -35), (-71, -18), (-77, -10), (-81, -3)],
    [(-17, 21), (-12, 28), (-6, 35), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (51, 12), (42, -1),
     (40, -15), (35, -24), (28, -33), (20, -35), (17, -29), (12, -17), (13, -6), (9, 4), (-8, 5), (-15, 11)],
    [(-10, 36), (-9, 43), (-2, 44), (-5, 48), (5, 53), (8, 57), (5, 62), (15, 69), (28, 71), (40, 67),
     (60, 70), (80, 73), (105, 78), (130, 72), (160, 70), (180, 68), (180, 64), (160, 60), (155, 52),
     (140, 45), (130, 35), (121, 30), (121, 23), (108, 21), (106, 10), (100, 13), (103, 1), (98, 8),
     (92, 22), (80, 15), (77, 8), (73, 20), (66, 25), (57, 25), (55, 22), (52, 17), (43, 13), (40, 20),
     (35, 28), (34, 32), (36, 36), (28, 36), (26, 40), (23, 36), (20, 40), (13, 45), (16, 38), (12, 38),
     (9, 44), (3, 43), (0, 39), (-6, 36)],
    [(114, -22), (122, -17), (130, -12), (137, -12), (142, -11), (146, -19), (153, -26), (150, -37),
     (141, -38), (131, -31), (115, -34)],
    [(-5, 50), (1, 51), (-2, 56), (-5, 58), (-6, 55)],
    [(130, 31), (140, 35), (142, 40), (141, 45), (139, 40), (132, 34)],
    [(109, 1), (117, 7), (119, 1), (116, -4), (110, -3)],
    [(95, 5), (104, -6), (106, -5), (98, 2)],
    [(44, -25), (47, -25), (50, -15), (49, -12), (44, -17)],
    [(-180, -76), (180, -76), (180, -90), (-180, -90)],
)
CELL = 4  # degrees per land cell


def _inside(x, y, poly):
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def land_cells(outlines=CONTINENTS, cell=CELL):
    """Rows of land: (south lat, [west lon of each land cell]) for every
    `cell`-degree band, the cells whose centre falls inside an outline."""
    rows = []
    for lat in range(-90, 90, cell):
        lons = [lon for lon in range(-180, 180, cell)
                if any(_inside(lon + cell / 2, lat + cell / 2, p) for p in outlines)]
        if lons:
            rows.append((lat, lons))
    return rows


_LAND = land_cells()


def _wrap(lon):
    return (lon + 180.0) % 360.0 - 180.0


def _line(lon0, lon1, lat0, lat1, steps):
    return [(lon0 + (lon1 - lon0) * i / steps, lat0 + (lat1 - lat0) * i / steps) for i in range(steps + 1)]


def draw_projection_morph(cv, cx, cy, progress, radius, spin=0.0, land=demo.TEAL, ocean='#1c2533',
                          grid=demo.MUTED, equator=demo.ACCENT, rows=None, cell=CELL):
    """Draw the world centred at (`cx`, `cy`) at `progress` through
    `projection_morph` (0 globe, 1 flat map): the ocean face, land cells, a
    30-degree graticule and the equator. `spin` (degrees) turns the world
    eastward under the centre meridian, for a globe that rotates before or
    after it unrolls. `rows` is a `land_cells` result (default: a rough Earth)."""
    rows = _LAND if rows is None else rows
    span = visible_span(progress)

    def pt(lon, lat):
        x, y = projection_morph(lon, lat, progress, radius)
        return cx + x, cy + y

    edge = [pt(span, lat) for lat in range(-90, 91, 3)] + [pt(-span, lat) for lat in range(90, -91, -3)]
    paths.draw(cv, edge, ocean, fill=True)
    for lat, lons in rows:
        rel = sorted(_wrap(lon + spin) for lon in lons)
        runs = []
        for lon in rel:
            if runs and abs(lon - runs[-1][1]) < 1e-6:
                runs[-1][1] = lon + cell
            else:
                runs.append([lon, lon + cell])
        for a, b in runs:
            a, b = max(a, -span), min(b, span)
            if b <= a:
                continue
            steps = max(1, math.ceil((b - a) / 3))
            ring = _line(a, b, lat, lat, steps) + _line(b, a, lat + cell, lat + cell, steps)
            poly = [pt(*p) for p in ring]
            paths.draw(cv, poly, land, fill=True)
            paths.draw(cv, poly, land, width=1, closed=True)  # hides hairline seams between rows
    for m in range(-180, 180, 30):
        lon = _wrap(m + spin)
        if -span <= lon <= span:
            paths.draw(cv, [pt(lon, lat) for lat in range(-90, 91, 3)], grid, width=1, alpha=0.35)
    for lat in (-60, -30, 30, 60):
        paths.draw(cv, [pt(lon, lat) for lon, _ in _line(-span, span, 0, 0, 120)], grid, width=1, alpha=0.35)
    paths.draw(cv, edge, grid, width=1.5, closed=True, alpha=0.6)
    paths.draw(cv, [pt(lon, 0) for lon, _ in _line(-span, span, 0, 0, 120)], equator, width=2)


def draw(n, cv):
    t = demo.phase(n, 0.7, 2.5)
    p = t * t * (3 - 2 * t)  # smoothstep: a gentle start and landing, steady through the unroll
    turn = vb.ease_in_out_quart(demo.phase(n, 0.0, 1.2))
    radius = 175 + (132 - 175) * p  # a big globe, then a map that fills the frame's width
    draw_projection_morph(cv, demo.W / 2, demo.H / 2, p, radius, spin=-70 * (1 - turn))
    cv.mark('world', demo.W / 2 - math.pi * 132, demo.H / 2 - radius, 2 * math.pi * 132, 2 * radius)


CAPABILITY = Capability(
    id='projection-morph',
    name='Projection morph',
    family='broadcast',
    group='Maps',
    aliases=('globe to map morph', 'map projection transition', 'globe unroll'),
    definition='A globe flattens out into a rectangular world map, its continents and grid lines gliding '
               'continuously from their places on the sphere to their places on the flat projection.',
    phrasings=('turn the spinning globe into a flat world map',
               'unroll the earth into a map',
               'morph between a globe and a flat map projection'),
    related=('sphere-to-grid-morph', 'shape-morph', 'particle-morph', 'superformula-morph',
             'morphing-shape-ident', 'polar-coordinate-warp'),
    api=('videobuilder.capabilities.broadcast.projection_morph.projection_morph',
         'videobuilder.capabilities.broadcast.projection_morph.draw_projection_morph',
         'videobuilder.capabilities.broadcast.projection_morph.land_cells'),
    demo=lambda: demo.film(draw),
)

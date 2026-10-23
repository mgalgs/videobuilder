"""Zoom-to-location map: the map camera flies from a wide view of a region
down to one place on it, the centre gliding onto the target while the scale
climbs, then a pin marks the spot. The flight is the smooth zoom-and-pan
path of van Wijk and Nuij: a target far off-screen makes the camera pull
back a little first, then sweep in."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def fly_to(p, start, end, rho=1.42):
    """The map camera at progress `p` (0 -> 1) on the flight from view
    `start` to view `end`, each `(cx, cy, width)`: the map point at the
    centre of the frame and how many map units the frame spans across.
    Returns the `(cx, cy, width)` in between. Pan and zoom are one motion:
    the apparent speed stays even while the scale changes by orders of
    magnitude, and `rho` sets how far it zooms out on the way when the
    target starts off-screen (higher: more). Ease `p` yourself; at 0 and 1
    the view is exactly `start` and `end`."""
    (x0, y0, w0), (x1, y1, w1) = start, end
    p = vb.clamp01(p)
    dx, dy = x1 - x0, y1 - y0
    u1 = math.hypot(dx, dy)
    if u1 < 1e-9 * max(w0, w1):  # no pan: a pure zoom, even in log space
        return x0 + dx * p, y0 + dy * p, vb.log_lerp(w0, w1, p)
    r2u = rho * rho * u1
    b0 = (w1 * w1 - w0 * w0 + rho ** 2 * r2u * u1) / (2 * w0 * r2u)
    b1 = (w1 * w1 - w0 * w0 - rho ** 2 * r2u * u1) / (2 * w1 * r2u)
    r0 = math.log(-b0 + math.sqrt(b0 * b0 + 1))
    r1 = math.log(-b1 + math.sqrt(b1 * b1 + 1))
    s = (r1 - r0) / rho * p
    u = w0 / rho ** 2 * (math.cosh(r0) * math.tanh(rho * s + r0) - math.sinh(r0))
    w = w0 * math.cosh(r0) / math.cosh(rho * s + r0)
    if p >= 1:
        return x1, y1, w1
    return x0 + dx / u1 * u, y0 + dy / u1 * u, w


def zoom_to_location(cv, draw_map, p, start, end, rho=1.42, ease=vb.ease_in_out_quart):
    """Draw the map at flight progress `p` (0 -> 1) from view `start` to
    view `end` (see `fly_to`). `draw_map(cv, x0, y0, x1, y1, scale)` draws
    the map in map units, given the part in view and the current screen px
    per map unit (divide stroke widths by it to keep them a constant size
    on screen). Returns `to_screen(mx, my) -> (x, y)` for this frame, to
    place labels and pins in frame px on top.

    In a film: `to_screen = zoom_to_location(cv, my_map, shot.p, WIDE, CITY)`."""
    w, h = cv.width, cv.height
    cx, cy, span = fly_to(ease(vb.clamp01(p)), start, end, rho)
    s = w / span
    with cv.layer(dx=w / 2 - cx * s, dy=h / 2 - cy * s, scale=s):
        draw_map(cv, cx - w / 2 / s, cy - h / 2 / s, cx + w / 2 / s, cy + h / 2 / s, s)
    return lambda mx, my: (w / 2 + (mx - cx) * s, h / 2 + (my - cy) * s)


# ---- the demo: a made-up coast, flown in to one street corner ----

WATER, LAND, PARK = '#0e1015', '#1e2129', '#1d2a27'
TARGET = (5480.0, 2470.0)
WIDE = (4000.0, 2250.0, 8400.0)
CLOSE = (TARGET[0], TARGET[1], 420.0)
CITIES = (('Harrow', 1900, 1500), ('Lindqvist', 3100, 3100), ('Port Aster', 5480, 2470),
          ('Calder', 6500, 1350), ('Weybridge', 4300, 1050), ('Esk', 2700, 2100))
ROADS = ((0, 5, 1, 2, 3), (5, 4, 3), (4, 2))
DISTRICT = 700.0  # half-size of the street grid around the target, map units
STREET = 46.0


def _coast():
    pts, (cx, cy) = [], (4000, 2250)
    for i in range(160):
        a = 2 * math.pi * i / 160
        r = (1 + 0.09 * math.sin(3 * a + 1) + 0.06 * math.sin(7 * a + 2) + 0.03 * math.sin(17 * a)
             + 0.015 * math.sin(41 * a + 0.5))
        pts.append((cx + 3150 * r * math.cos(a), cy + 1650 * r * math.sin(a)))
    return pts


COAST = _coast()
RIVER = [(5480 + 900 * math.sin(t / 14) * 0.15 + (t - 20) * 18, 2470 - 1500 + t * 60 + 40 * math.sin(t / 3))
         for t in range(0, 41)]


def _hash(i, j):
    return ((i * 73856093) ^ (j * 19349663)) % 1000 / 1000


def _streets(cv, x0, y0, x1, y1, s, alpha):
    tx, ty = TARGET
    gx0, gy0 = max(x0, tx - DISTRICT), max(y0, ty - DISTRICT)
    gx1, gy1 = min(x1, tx + DISTRICT), min(y1, ty + DISTRICT)
    if gx1 <= gx0 or gy1 <= gy0:
        return
    i0, i1 = math.floor((gx0 - tx) / STREET), math.ceil((gx1 - tx) / STREET)
    j0, j1 = math.floor((gy0 - ty) / STREET), math.ceil((gy1 - ty) / STREET)
    for i in range(i0, i1):
        for j in range(j0, j1):
            k = _hash(i, j)
            if k < 0.55:
                inset = STREET * 0.18
                bx, by = tx + i * STREET + inset, ty + j * STREET + inset
                color = PARK if k < 0.06 else '#2b2f3a'
                cv.rect(bx, by, STREET - 2 * inset, STREET - 2 * inset, color, radius=2, alpha=alpha)
    for i in range(i0, i1 + 1):
        x = tx + i * STREET
        cv.line(x, gy0, x, gy1, demo.LINE, width=(3 if i % 4 else 6) / s, alpha=alpha)
    for j in range(j0, j1 + 1):
        y = ty + j * STREET
        cv.line(gx0, y, gx1, y, demo.LINE, width=(3 if j % 4 else 6) / s, alpha=alpha)


def _map(cv, x0, y0, x1, y1, s):
    cv.fill(WATER)
    vb.paths.draw(cv, COAST, LAND, fill=True)
    vb.paths.draw(cv, COAST, '#3a4050', width=2.5 / s, closed=True)
    vb.paths.draw(cv, RIVER, '#24344a', width=max(10 / s, 26))
    _streets(cv, x0, y0, x1, y1, s, vb.clamp01((s - 0.35) / 0.6))
    for road in ROADS:
        vb.paths.draw(cv, [CITIES[k][1:] for k in road], demo.TEAL, width=4 / s, alpha=0.85)


def _pin(cv, x, y, p):
    """A map pin dropping onto (x, y) with a ripple, `p` 0 -> 1."""
    if p <= 0:
        return
    drop = vb.ease_out_back(vb.clamp01(p / 0.6))
    ring = vb.clamp01((p - 0.35) / 0.65)
    if ring > 0:
        cv.arc(x, y, 14 + 60 * ring, 0, 2 * math.pi, demo.ACCENT, width=3, alpha=1 - ring)
    cv.sector(x, y, 7, 0, 2 * math.pi, demo.ACCENT, alpha=min(1, p * 4))
    hy = y - 30 - 50 * (1 - drop)
    with cv.layer(opacity=min(1, p * 4)):
        c = cv.ctx
        c.new_path()
        c.move_to(x, y - 6)
        c.arc(x, hy, 20, math.radians(140), math.radians(40))
        c.close_path()
        c.set_source_rgb(*vb.canvas.rgba(demo.ACCENT)[:3])
        c.fill()
        cv.sector(x, hy, 8, 0, 2 * math.pi, demo.BG)


def _draw(n, cv):
    flight = demo.phase(n, 0.2, 1.7)
    to_screen = zoom_to_location(cv, _map, flight, WIDE, CLOSE)
    names = 1 - vb.clamp01(flight * 2.2)  # the region's labels fade as the camera dives
    f = demo.font(20, 700)
    label_fade = 1 - demo.phase(n, 1.45, 1.6)  # the small target label is gone before the pin lands
    for i, (name, mx, my) in enumerate(CITIES):
        x, y = to_screen(mx, my)
        target = i == 2
        demo.dot(cv, x, y, r=7, color=demo.ACCENT if target else demo.INK, alpha=1 if target else names)
        if names > 0 or (target and label_fade > 0):
            label = demo.font(20, 800) if target else f
            vb.text.draw(cv, [name], label, x + 14, y - 30, demo.ACCENT if target else demo.MUTED,
                         alpha=label_fade if target else names)
    x, y = to_screen(*TARGET)
    _pin(cv, x, y, demo.phase(n, 1.6, 2.3))
    title = demo.phase(n, 1.8, 2.05)
    if title > 0:
        demo.word(cv, 'Port Aster', x, y + 52 - 10 * (1 - title), size=30, alpha=title)


CAPABILITY = Capability(
    id='zoom-to-location-map',
    name='Zoom-to-location map',
    family='broadcast',
    group='Maps',
    aliases=('fly-to camera', 'map camera zoom', 'map fly-in'),
    definition='A map seen from far away glides and magnifies in one smooth move until a single place '
               'fills the frame, where a marker then lands on it.',
    phrasings=('zoom the map in from the whole region down to the city',
               'fly the map camera to this address and drop a pin',
               'start wide on the country, then dive into the spot where it happened'),
    related=('scale-zoom-through', 'canvas-pan-and-zoom', 'ui-walkthrough-camera-zoom', 'fly-through',
             'zoom-through', 'drone-flyover'),
    api=('videobuilder.capabilities.broadcast.zoom_to_location_map.zoom_to_location',
         'videobuilder.capabilities.broadcast.zoom_to_location_map.fly_to'),
    demo=lambda: demo.film(_draw),
)

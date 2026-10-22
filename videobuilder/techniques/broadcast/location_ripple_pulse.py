"""Location ripple pulse: a marker dot on a map beats steadily, and with each
beat a ring leaves it and widens out over the streets, thinning to nothing --
the "this is where it's happening" ping of news and data maps. The rings are
`shapes/ripple_rings.py`; this adds the marker that drives them."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique
from ..shapes.ripple_rings import ripple_rings


def location_pulse(cv, x, y, t, radius=200, every=0.8, life=2.2, color=demo.ACCENT, size=11,
                   rim=demo.INK, width=3, count=None):
    """Draw a pulsing location marker at (x, y), `t` seconds after its first
    ping (a negative `t` shows the marker alone, not yet pinging).

    Every `every` seconds a ring of `color` leaves the marker and grows to
    `radius` over `life` seconds while it fades; the dot kicks as each ring
    leaves and a soft halo breathes with it. `size` is the dot's radius and
    `rim` its outline colour (None for none); `count` stops after that many
    rings. Returns the marker's Box, for labels and callouts."""
    ripple_rings(cv, x, y, t, radius=radius, every=every, life=life, color=color, width=width,
                 start_radius=size, count=count)
    beat = 0.0
    if t >= 0 and (count is None or t < count * every):
        beat = max(0.0, 1 - (t % every) / (every * 0.35))  # 1 at each ping, decaying
    halo = size * (2.2 + 0.8 * beat)
    demo.dot(cv, x, y, halo, color=color, alpha=0.18 + 0.14 * beat)
    r = size * (1 + 0.3 * beat)
    if rim:
        demo.dot(cv, x, y, r + 3, color=rim)
    demo.dot(cv, x, y, r, color=color)
    return vb.Box(x - halo, y - halo, 2 * halo, 2 * halo)


# The demo's map: a dark city grid crossed by a river, with two bridges.
STREET, BLOCK, PARK, WATER = '#141a22', '#232c38', '#22352c', '#2f4a78'
RIVER = [(230 + 50 * math.sin(i / 2.4), -20 + i * 40) for i in range(16)]


def _map(cv):
    cv.fill(STREET)
    step, gap = 64, 10
    for i, x in enumerate(range(-30, demo.W, step)):
        for j, y in enumerate(range(-40, demo.H, step)):
            shade = PARK if (i, j) in ((11, 2), (12, 2), (5, 6)) else BLOCK
            cv.rect(x + gap / 2, y + gap / 2, step - gap, step - gap, shade, radius=6)
    cv.line(0, 470, demo.W, 400, '#384556', width=9)  # an avenue cutting across
    paths.draw(cv, RIVER, WATER, width=48)
    paths.draw(cv, RIVER, '#4a6aa3', width=48, alpha=0.25)
    for by in (110, 330):
        bx = 230 + 50 * math.sin((by + 20) / 40 / 2.4)
        cv.line(bx - 42, by + 4, bx + 42, by - 4, '#8d98a8', width=7)


def draw(n, cv):
    _map(cv)
    x, y = demo.W * 0.62, demo.H * 0.45
    t = n / demo.FPS - 0.3
    box = location_pulse(cv, x, y, t, radius=190, every=0.75, life=2.0, width=4, size=10)
    cv.mark('marker', *box)
    f = demo.mono(18, 700)
    shown = demo.phase(n, 0.2, 0.6)
    vb.text.draw(cv, ['LIVE  ·  5TH & MAIN'], f, x + 30, y - 52, demo.INK, alpha=shown)


TECHNIQUE = Technique(
    id='location-ripple-pulse',
    name='Location ripple pulse',
    family='broadcast',
    group='Maps',
    aliases=('location pulse', 'radar ping on map', 'map ping', 'pulsing map marker'),
    definition='A dot marking a place on a map beats in a steady rhythm, sending out a ring with each beat '
               'that spreads across the map and fades away.',
    phrasings=('make the spot on the map ping like radar',
               'show where it is happening with circles pulsing out from the marker',
               'a live location dot with rings rippling out'),
    related=('ripple-rings', 'ripple', 'orbital-pulse', 'refraction-ripple', 'touch-ripple',
             'ridgeline-ripple'),
    api=('videobuilder.techniques.broadcast.location_ripple_pulse.location_pulse',
         'videobuilder.techniques.shapes.ripple_rings.ripple_rings'),
    demo=lambda: demo.film(draw),
)

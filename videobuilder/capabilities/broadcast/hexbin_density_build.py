"""Hexbin density build: scattered data points rain onto a chart and are
counted into a honeycomb of hexagonal bins, each cell deepening in colour as
more points land in it, until the density pattern stands out."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability
from ..shapes.hexagon_tile_reveal import hexagon


def hex_bin(px, py, ox, oy, size):
    """The axial (q, r) of the pointy-top hexagon of circumradius `size`,
    laid out with a cell centred on (ox, oy), that contains point (px, py)."""
    x, y = (px - ox) / size, (py - oy) / size
    q, r = math.sqrt(3) / 3 * x - y / 3, 2 / 3 * y
    cx, cz = round(q), round(r)
    cy = round(-q - r)
    dx, dy, dz = abs(cx - q), abs(cy + q + r), abs(cz - r)
    if dx > dy and dx > dz:
        cx = -cy - cz
    elif dy <= dz:
        cz = -cx - cy
    return cx, cz


def hex_center(q, r, ox, oy, size):
    """The centre of axial cell (q, r) in the layout `hex_bin` uses."""
    return ox + math.sqrt(3) * size * (q + r / 2), oy + 1.5 * size * r


def hexbin_build(cv, points, p, size=40, origin=(0.0, 0.0), ramp=('#23262f', '#4fc3b0', '#f4f4f2'), gap=3,
                 drop=0.12, fall=30, dot=2.5, dot_color=demo.INK, peak=None):
    """Draw a hexbin of `points` (a list of (x, y)) built up to progress `p`
    (0 -> 1): points arrive in list order, each falling `fall` px and fading
    in as a small dot over `drop` of the build, and once landed it counts
    toward its hexagonal bin. Every non-empty bin is a hexagon of circumradius
    `size` (less `gap` grout) coloured along `ramp` by its count over `peak`
    (default the fullest bin's final count), so the colour scale holds still
    while the cells fill. Returns {(q, r): count} at this progress."""
    ox, oy = origin
    bins = [hex_bin(x, y, ox, oy, size) for x, y in points]
    if peak is None:
        final = {}
        for b in bins:
            final[b] = final.get(b, 0) + 1
        peak = max(final.values(), default=1)
    n = len(points)
    span = 1 - drop
    counts, falling = {}, []
    for i, (pt, b) in enumerate(zip(points, bins)):
        k = vb.clamp01((p - span * i / max(1, n - 1)) / drop) if drop > 0 else float(p >= i / max(1, n - 1))
        if k >= 1:
            counts[b] = counts.get(b, 0) + 1
        elif k > 0:
            counts[b] = counts.get(b, 0) + k   # the cell starts warming as the dot lands
            falling.append((pt, k))
    for (q, r), c in counts.items():
        t = min(1.0, c / peak)
        cx, cy = hex_center(q, r, ox, oy, size)
        hexagon(cv, cx, cy, (size - gap / 2) * min(1.0, 0.55 + 2 * t), _ramp(ramp, t), alpha=min(1.0, 0.35 + 3 * t))
    for (x, y), k in falling:
        e = vb.ease_out_quint(k)
        demo.dot(cv, x, y - fall * (1 - e), dot, dot_color, alpha=1 - k * k)
    return counts


def _ramp(colors, t):
    t = vb.clamp01(t) * (len(colors) - 1)
    i = min(int(t), len(colors) - 2)
    return kit.mix(colors[i], colors[i + 1], t - i)


def sample_points(n, clusters, seed=0):
    """`n` points drawn from gaussian `clusters` of (cx, cy, sigma, weight),
    shuffled so a build fills every cluster at once."""
    rng = random.Random(seed)
    total = sum(c[3] for c in clusters)
    out = []
    for cx, cy, sigma, weight in clusters:
        for _ in range(round(n * weight / total)):
            out.append((rng.gauss(cx, sigma), rng.gauss(cy, sigma * 0.8)))
    rng.shuffle(out)
    return out


X0, Y0, X1, Y1 = 110, 50, 820, 490
POINTS = [(x, y) for x, y in sample_points(
    1600, ((420, 330, 75, 5), (610, 220, 48, 3), (300, 170, 35, 1.5), (470, 270, 160, 2)), seed=4)
    if X0 < x < X1 and Y0 < y < Y1]
RAMP = ('#2a2c33', '#4fc3b0', '#f2b705', '#ef5b4c')


def draw(n, cv):
    cv.line(X0 - 10, Y1 + 10, X1, Y1 + 10, demo.MUTED, width=2)
    cv.line(X0 - 10, Y0, X0 - 10, Y1 + 10, demo.MUTED, width=2)
    with cv.clip(X0 - 8, Y0, X1 - X0 + 8, Y1 - Y0 + 8):
        hexbin_build(cv, POINTS, demo.phase(n, 0.2, 2.6), size=17, origin=(demo.W / 2, demo.H / 2),
                     ramp=RAMP, drop=0.1)
    # density legend
    for i in range(6):
        demo.dot(cv, X1 + 50, Y1 - 20 - i * 24, 8, _ramp(RAMP, i / 5))
    vb.text.draw(cv, ['more'], kit.font(14, 700), X1 + 34, Y1 - 172, demo.MUTED)
    cv.mark('hexbin', X0, Y0, X1 - X0, Y1 - Y0)


CAPABILITY = Capability(
    id='hexbin-density-build',
    name='Hexbin density build',
    family='broadcast',
    group='Charts',
    aliases=('hexbin plot', 'hexagonal binning', 'hex density map', 'hex heatmap'),
    definition='Dots pour onto a chart and are tallied into a honeycomb of hexagon cells that '
               'glow hotter the more dots fall into them, until the dense areas stand out.',
    phrasings=('show the data piling up into a hexagon heatmap',
               'animate a hex-binned scatter plot filling in',
               'points dropping in and the hex cells getting brighter where they cluster'),
    related=('hexagon-tile-reveal', 'dot-density-map', 'data-bending', 'mandelbulb-raymarch',
             'choropleth-fill', 'circle-packing'),
    api=('videobuilder.capabilities.broadcast.hexbin_density_build.hexbin_build',
         'videobuilder.capabilities.broadcast.hexbin_density_build.hex_bin',
         'videobuilder.capabilities.broadcast.hexbin_density_build.sample_points',
         'videobuilder.capabilities.shapes.hexagon_tile_reveal.hexagon'),
    demo=lambda: demo.film(draw),
)

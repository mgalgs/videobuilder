"""Choropleth Fill: the regions of a map start blank, then each floods with a
colour from a ramp that stands for its value, region by region, while a
legend explains the scale."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

RAMP = ('#1d3b4f', '#2f7f86', '#7fbf8e', '#f2d27a', '#ee8a4f')  # low -> high


def ramp(value, stops=RAMP):
    """The colour for `value` (0 -> 1) on the evenly spaced colour `stops`,
    as an (r, g, b) tuple of 0-255 channels."""
    v = vb.clamp01(value) * (len(stops) - 1)
    i = min(int(v), len(stops) - 2)
    a, b = vb.rgba(stops[i]), vb.rgba(stops[i + 1])
    t = v - i
    return tuple(255 * (x + (y - x) * t) for x, y in zip(a[:3], b[:3]))


def fill_order(regions, mode='sweep'):
    """A start time 0 -> 1 per region: 'sweep' goes left to right by each
    region's centre, 'random' is a seeded shuffle."""
    if mode == 'random':
        rnd = random.Random(len(regions))
        return [rnd.random() for _ in regions]
    xs = [sum(x for x, _ in r) / len(r) for r in regions]
    lo, hi = min(xs), max(xs)
    return [(x - lo) / ((hi - lo) or 1) for x in xs]


def choropleth_fill(cv, regions, values, p, stops=RAMP, empty='#2a2f3a', edge='#0f1218',
                    edge_width=2.0, order=None, spread=0.7):
    """Draw `regions` (closed point lists) at progress `p` (0 -> 1): each
    starts as `empty` and eases to `ramp(values[i], stops)`. Region i begins
    at `order[i] * spread` (default: a left-to-right sweep) and takes the
    remaining `1 - spread` of the timeline to fill, flashing a little bright
    as it lands. Borders are stroked in `edge` on top."""
    order = fill_order(regions) if order is None else order
    c = cv.ctx
    e = vb.rgba(empty)
    for poly, v, o in zip(regions, values, order):
        t = vb.clamp01((p - o * spread) / (1 - spread))
        k = 1 - (1 - t) ** 3
        col = ramp(v, stops)
        rgb = [e[j] * 255 + (col[j] - e[j] * 255) * k for j in range(3)]
        glow = math.sin(math.pi * t) * 0.35
        rgb = [x + (255 - x) * glow for x in rgb]
        c.new_path()
        c.move_to(*poly[0])
        for pt in poly[1:]:
            c.line_to(*pt)
        c.close_path()
        c.set_source_rgba(*vb.rgba(tuple(rgb)))
        c.fill_preserve()
        c.set_source_rgba(*vb.rgba(edge))
        c.set_line_width(edge_width)
        c.stroke()


def legend(cv, x, y, w, h, p=1.0, stops=RAMP, low='Low', high='High', font=None, ink='#e8e6e1'):
    """A horizontal colour-ramp key at (x, y, w, h), revealed left to right
    by `p`, labelled `low` and `high` beneath its ends."""
    n = 48
    for i in range(int(n * vb.clamp01(p))):
        cv.rect(x + w * i / n, y, w / n + 1, h, ramp(i / (n - 1), stops))
    cv.outline(x, y, w, h, ink, width=1.5, alpha=0.5)
    f = font or demo.font(24, 600)
    vb.text.draw(cv, [low], f, x, y + h + 10, ink, alpha=0.8)
    lw, _ = vb.text.block_size([high], f)
    vb.text.draw(cv, [high], f, x + w - lw, y + h + 10, ink, alpha=0.8)


def patchwork(cx, cy, w, h, cols=15, rows=9, seed=3):
    """A made-up map: a jittered grid of four-sided regions inside an
    irregular blob, plus a smooth seeded value per region. Returns
    `(regions, values)`. For demos and placeholders, not geography."""
    rnd = random.Random(seed)
    cw, ch = w / cols, h / rows
    pts = {(i, j): (cx - w / 2 + i * cw + rnd.uniform(-0.3, 0.3) * cw * (0 < i < cols),
                    cy - h / 2 + j * ch + rnd.uniform(-0.3, 0.3) * ch * (0 < j < rows))
           for i in range(cols + 1) for j in range(rows + 1)}
    regions, values = [], []
    for i in range(cols):
        for j in range(rows):
            u, v = (i + 0.5) / cols * 2 - 1, (j + 0.5) / rows * 2 - 1
            a = math.atan2(v, u)
            edge = 0.8 + 0.12 * math.sin(3 * a + 1) + 0.07 * math.cos(5 * a)
            if math.hypot(u, v) > edge:
                continue
            regions.append([pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]])
            val = 0.5 + 0.3 * math.sin(2.2 * u + 0.6) * math.cos(1.7 * v) + 0.25 * u + rnd.uniform(-0.12, 0.12)
            values.append(vb.clamp01(val))
    return regions, values


REGIONS, VALUES = patchwork(demo.W / 2, demo.H / 2 - 30, 660, 380)


def draw(n, cv):
    choropleth_fill(cv, REGIONS, VALUES, demo.phase(n, 0.3, 2.4), empty='#2a2f3a', edge=demo.BG,
                    edge_width=1.5)
    lw = 280
    legend(cv, (demo.W - lw) / 2, demo.H - 72, lw, 12, demo.phase(n, 0.2, 0.9), font=demo.font(14, 600),
           ink=demo.INK)
    cv.mark('map', demo.W / 2 - 330, demo.H / 2 - 220, 660, 380)


TECHNIQUE = Technique(
    id='choropleth-fill',
    name='Choropleth fill',
    family='broadcast',
    group='Maps',
    aliases=('choropleth map', 'thematic map fill', 'heat map by region'),
    definition='Blank regions on a map fill in one after another, each taking a shade from a colour '
               'scale that stands for its number, until the whole map reads as data.',
    phrasings=('colour in each state on the map by its value',
               'make the map regions light up in shades for the election results',
               'animate the counties filling with colour like a data map'),
    related=('area-fill-sweep', 'hue-cycle-fill', 'shape-fill-sweep', 'heatmap-fill', 'color-fill-rise',
             'radar-chart-fill'),
    api=('videobuilder.techniques.broadcast.choropleth_fill.choropleth_fill',
         'videobuilder.techniques.broadcast.choropleth_fill.ramp',
         'videobuilder.techniques.broadcast.choropleth_fill.legend',
         'videobuilder.techniques.broadcast.choropleth_fill.fill_order',
         'videobuilder.techniques.broadcast.choropleth_fill.patchwork'),
    demo=lambda: demo.film(draw),
)

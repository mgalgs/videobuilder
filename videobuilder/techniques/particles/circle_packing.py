"""Circle packing: dots seeded across a region swell at different rates,
shove their neighbours aside as they grow, and stop once they are wedged in,
until the region is tiled with touching circles of mixed sizes."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@functools.lru_cache(maxsize=16)
def pack_circles(x, y, w, h, cols=14, rows=8, steps=80, gap=2.0, seed=0):
    """Simulate circles packing the box (x, y, w, h). They start as small dots
    on a jittered `cols` x `rows` grid, each with its own growth rate; every
    step they grow, overlapping pairs push apart, walls hold them in, and a
    circle that cannot fit any more stops growing. `gap` is the space left
    between neighbours. Returns `steps + 1` snapshots, each a tuple of
    `(cx, cy, r)` per circle, the same for the same arguments (and cached)."""
    rng = random.Random(seed)
    cw, ch = w / cols, h / rows
    pts = [[x + (i + 0.5 + rng.uniform(-0.3, 0.3)) * cw, y + (j + 0.5 + rng.uniform(-0.3, 0.3)) * ch]
           for j in range(rows) for i in range(cols)]
    cell = min(cw, ch)
    r = [cell * 0.06] * len(pts)
    rate = [cell * rng.uniform(0.004, 0.014) for _ in pts]
    growing = [True] * len(pts)
    snaps = [tuple((px, py, pr) for (px, py), pr in zip(pts, r))]
    for _ in range(steps):
        for i in range(len(pts)):
            if growing[i]:
                r[i] += rate[i]
        for _ in range(5):
            squeeze = [0.0] * len(pts)      # what is still overlapping after the last pass
            for i in range(len(pts)):
                xi, yi = pts[i]
                for k in range(i + 1, len(pts)):
                    dx, dy = pts[k][0] - xi, pts[k][1] - yi
                    need = r[i] + r[k] + gap
                    if abs(dx) >= need or abs(dy) >= need:
                        continue
                    d = math.hypot(dx, dy) or 1e-6
                    over = need - d
                    if over <= 0:
                        continue
                    squeeze[i] = max(squeeze[i], over)
                    squeeze[k] = max(squeeze[k], over)
                    # the bigger circle shoves the smaller one further
                    share = r[i] / (r[i] + r[k])
                    ux, uy = dx / d, dy / d
                    pts[i][0] -= ux * over * (1 - share)
                    pts[i][1] -= uy * over * (1 - share)
                    pts[k][0] += ux * over * share
                    pts[k][1] += uy * over * share
            for i, p in enumerate(pts):
                lim = min(r[i], w / 2, h / 2)
                p[0] = min(max(p[0], x + lim), x + w - lim)
                p[1] = min(max(p[1], y + lim), y + h - lim)
        for i in range(len(pts)):
            if growing[i] and squeeze[i] > rate[i] * 0.25:
                growing[i] = False          # wedged in: no room to push into, hold this size
                r[i] = max(cell * 0.06, r[i] - squeeze[i])
        snaps.append(tuple((px, py, pr) for (px, py), pr in zip(pts, r)))
    return tuple(snaps)


def circle_packing_at(snaps, p):
    """The packing at progress `p` (0 -> 1) through `snaps` from `pack_circles`,
    blended between the two nearest snapshots so motion is smooth at any frame rate."""
    t = vb.clamp01(p) * (len(snaps) - 1)
    i = min(int(t), len(snaps) - 2)
    f = t - i
    return [(ax + (bx - ax) * f, ay + (by - ay) * f, ar + (br - ar) * f)
            for (ax, ay, ar), (bx, by, br) in zip(snaps[i], snaps[i + 1])]


def draw_circle_packing(cv, snaps, p, colors, alpha=1.0, seed=0):
    """Draw the packing from `pack_circles` at progress `p`, each circle a solid
    disc in a colour picked from `colors` (stable per circle for `seed`).
    Returns the circles drawn as `(cx, cy, r)`."""
    rng = random.Random(seed)
    circles = circle_packing_at(snaps, p)
    for cx, cy, r in circles:
        cv.sector(cx, cy, r, 0, 2 * math.pi, rng.choice(colors), alpha=alpha)
    return circles


BOX = (90, 50, demo.W - 180, demo.H - 100)


def draw(n, cv):
    snaps = pack_circles(*BOX, seed=3)
    cv.outline(*BOX, demo.LINE, width=2)
    colors = (demo.TEAL, demo.TEAL, demo.MUTED, demo.INK, demo.ACCENT)
    draw_circle_packing(cv, snaps, demo.phase(n, 0.3, 2.7), colors, seed=3)
    cv.mark('region', *BOX)


TECHNIQUE = Technique(
    id='circle-packing',
    name='Circle packing',
    family='particles',
    group='Tiling & patterns',
    aliases=('circle packing animation', 'sphere packing', 'packed circles'),
    definition='Small dots scattered over an area swell to different sizes, nudging one another aside, '
               'until the whole area is filled with snugly touching circles.',
    phrasings=('grow a bunch of circles until they fill the box without overlapping',
               'bubbles that expand and jostle until they pack the space tight',
               'fill the shape with packed dots of different sizes that grow in'),
    related=('circle-pop', 'pie-sweep', 'radial-stagger', 'shape-boolean-merge', 'radial-repeater',
             'geometric-loop'),
    api=('videobuilder.techniques.particles.circle_packing.pack_circles',
         'videobuilder.techniques.particles.circle_packing.draw_circle_packing',
         'videobuilder.techniques.particles.circle_packing.circle_packing_at'),
    demo=lambda: demo.film(draw),
)

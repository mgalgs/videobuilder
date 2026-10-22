"""Cymatics: sand scattered on a vibrating square plate drifts off the parts
that shake and gathers on the still nodal lines, drawing a Chladni figure."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def chladni(x, y, m=2, n=5):
    """The standing-wave height at (x, y) on a unit square plate in mode
    (`m`, `n`), with x and y in [0, 1]. It is zero on the nodal lines, where
    grains come to rest; swapping `m` and `n` gives the same lines."""
    return (math.cos(n * math.pi * x) * math.cos(m * math.pi * y)
            - math.cos(m * math.pi * x) * math.cos(n * math.pi * y))


def _grad(x, y, m, n):
    a, b = n * math.pi, m * math.pi
    gx = -a * math.sin(a * x) * math.cos(b * y) + b * math.sin(b * x) * math.cos(a * y)
    gy = -b * math.cos(a * x) * math.sin(b * y) + a * math.cos(b * x) * math.sin(a * y)
    return gx, gy


@lru_cache(maxsize=16)
def chladni_paths(m=2, n=5, count=2400, steps=40, seed=7):
    """Each grain's journey from a random spot on the plate to the nearest
    nodal line of mode (`m`, `n`): a tuple of `count` paths, each `steps + 1`
    (x, y) points in [0, 1] spaced evenly along the way, first the scattered
    start, last the resting spot. Cached, so a film can call it every frame."""
    rng = random.Random(seed)
    paths = []
    for _ in range(count):
        x, y = rng.random(), rng.random()
        pts, lens = [(x, y)], [0.0]
        for _ in range(60):
            f = chladni(x, y, m, n)
            gx, gy = _grad(x, y, m, n)
            g2 = gx * gx + gy * gy + 1e-6
            dx, dy = -0.5 * f * gx / g2, -0.5 * f * gy / g2  # a damped step toward f = 0
            d = math.hypot(dx, dy)
            if d > 0.01:
                dx, dy = dx * 0.01 / d, dy * 0.01 / d
            x, y = min(1.0, max(0.0, x + dx)), min(1.0, max(0.0, y + dy))
            pts.append((x, y))
            lens.append(lens[-1] + math.hypot(x - pts[-2][0], y - pts[-2][1]))
        total = lens[-1] or 1.0
        path, j = [], 0
        for s in range(steps + 1):  # resample evenly by distance travelled
            want = total * s / steps
            while j < len(lens) - 2 and lens[j + 1] < want:
                j += 1
            seg = lens[j + 1] - lens[j]
            t = (want - lens[j]) / seg if seg > 0 else 0.0
            t = min(1.0, max(0.0, t))
            (x0, y0), (x1, y1) = pts[j], pts[j + 1]
            path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        paths.append(tuple(path))
    return tuple(paths)


def cymatics(cv, x, y, size, progress, m=2, n=5, count=2400, color=demo.ACCENT, grain=1.1,
             shake=4.0, frame=0, seed=7):
    """Draw grains on a `size`-px square plate whose top-left is (x, y),
    `progress` 0 -> 1 of the way from evenly scattered to settled on the
    nodal lines of mode (`m`, `n`). Grains jitter by up to `shake` px while
    they travel, calming as they settle; `frame` reseeds that jitter so it
    flickers from frame to frame. `grain` is each grain's radius in px."""
    p = vb.clamp01(progress)
    paths = chladni_paths(m, n, count, 40, seed)
    last = len(paths[0]) - 1
    k = p * last
    i = min(int(k), last - 1)
    t = k - i
    amp = shake * (1 - p) ** 1.5
    rng = random.Random(frame * 7919 + seed)
    ctx = cv.ctx
    ctx.set_source_rgba(*vb.canvas.rgba(color))
    for path in paths:
        (x0, y0), (x1, y1) = path[i], path[i + 1]
        px = x + size * (x0 + (x1 - x0) * t) + amp * (rng.random() - 0.5)
        py = y + size * (y0 + (y1 - y0) * t) + amp * (rng.random() - 0.5)
        ctx.rectangle(px - grain, py - grain, 2 * grain, 2 * grain)
    ctx.fill()


def draw(n, cv):
    size = 420
    x, y = (demo.W - size) / 2, (demo.H - size) / 2
    cv.rect(x - 8, y - 8, size + 16, size + 16, '#1b2028', radius=6)
    cv.outline(x - 8, y - 8, size + 16, size + 16, demo.LINE, width=2, radius=6)
    p = demo.phase(n, 0.3, 2.5)
    cymatics(cv, x, y, size, 1 - (1 - p) ** 2, frame=n)
    cv.mark('plate', x, y, size, size)


TECHNIQUE = Technique(
    id='cymatics',
    name='Cymatics',
    family='particles',
    group='Interaction fields',
    aliases=('Chladni figures', 'Chladni pattern', 'standing wave plate'),
    definition='Grains spread over a vibrating plate jiggle away from the parts that move and pile up '
               'along the lines that stay still, so a symmetric pattern draws itself out of the noise.',
    phrasings=('sand on a vibrating plate forming a pattern',
               'particles that shake into sound-wave shapes',
               'like the salt-on-a-speaker experiment where lines appear'),
    related=('caustics', 'wave-stagger', 'ripple-rings', 'hypocycloid-spirograph',
             'op-art-vibrating-pattern', 'mandelbulb-raymarch'),
    api=('videobuilder.techniques.particles.cymatics.cymatics',
         'videobuilder.techniques.particles.cymatics.chladni',
         'videobuilder.techniques.particles.cymatics.chladni_paths'),
    demo=lambda: demo.film(draw),
)

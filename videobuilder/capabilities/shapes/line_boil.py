"""Line boil: an outline redrawn with a fresh, small wobble every couple of
frames, so a still shape shimmers as if each frame were inked again by hand."""
import math
import random

from ... import paths
from .. import _demo as demo
from ..schema import Capability


def boil(points, n, amount=3.0, every=2, seed=0, closed=True, step=6.0, waves=(5, 9, 14, 21, 29)):
    """`points` as hand-redrawn on frame `n`: resampled every ~`step` px,
    then each point pushed along the line's normal by a smooth wobble made
    of a few sine `waves` (cycles along the whole line) with seeded random
    phases and strengths. The wobble holds for `every` frames (2: on twos)
    and is re-drawn at the next step. `amount`: px of the largest push.
    Deterministic for (`seed`, `n`); a closed outline wobbles without a seam."""
    pts = list(points)
    total = paths.length(pts, closed)
    if len(pts) < 2 or total == 0:
        return pts
    count = max(3 if closed else 2, round(total / step) + (0 if closed else 1))
    pts = paths.resample(pts, count, closed)
    rnd = random.Random(f'{seed}:{n // max(1, every)}')
    weights = [rnd.uniform(0.5, 1.0) / (1 + k) for k in range(len(waves))]
    norm = amount / sum(weights)
    terms = [(c, rnd.uniform(0, 2 * math.pi), w * norm) for c, w in zip(waves, weights)]
    span = count if closed else count - 1
    out = []
    for i, (x, y) in enumerate(pts):
        (px, py), (nx, ny) = (pts[i - 1], pts[(i + 1) % count]) if closed else \
            (pts[max(i - 1, 0)], pts[min(i + 1, count - 1)])
        tx, ty = nx - px, ny - py
        d = math.hypot(tx, ty) or 1.0
        u = 2 * math.pi * i / span
        push = sum(a * math.sin(c * u + ph) for c, ph, a in terms)
        out.append((x + ty / d * push, y - tx / d * push))
    return out


def draw_boil(cv, points, n, color, width=4, fill=None, closed=True, alpha=1.0, **kw):
    """Draw `points` boiling on frame `n` (see `boil`, which `kw` goes to):
    filled with `fill` when given, then stroked in `color`."""
    pts = boil(points, n, closed=closed, **kw)
    if fill and closed:
        paths.draw(cv, pts, fill, fill=True, alpha=alpha)
    paths.draw(cv, pts, color, width=width, closed=closed, alpha=alpha)
    return pts


def _star(cx, cy, r, lobes=5, depth=0.24, k=240):
    """A soft, rounded star: a circle whose radius swells into `lobes` bumps."""
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k
        rr = r * (1 - depth + depth * math.cos(lobes * (a + math.pi / 2)))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


STAR = _star(demo.W / 2, demo.H / 2 + 12, 205)


def draw(n, cv):
    pts = draw_boil(cv, STAR, n, demo.INK, width=4, fill='#1f2633', amount=3.5, every=3, seed=11)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv.mark('outline', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='line-boil',
    name='Line boil',
    family='shapes',
    group='Hand-drawn & traditional',
    aliases=('boiling line', 'hand-drawn jitter', 'rough outline', 'sketch wobble', 'line jitter'),
    definition='A shape that stays put while its outline is re-wobbled slightly every two or three '
               'frames, so the line seems to crawl as though freshly hand-drawn each time.',
    phrasings=('make the outline shimmer like it was drawn by hand frame by frame',
               'give the shape that wiggly, redrawn cartoon line',
               'the edges should quiver like a hand-animated sketch'),
    related=('jitter-and-boil-text', 'streamlines', 'stroke-draw-on', 'curl-noise-flow', 'line-weave',
             'ink-bleed'),
    api=('videobuilder.capabilities.shapes.line_boil.boil',
         'videobuilder.capabilities.shapes.line_boil.draw_boil'),
    demo=lambda: demo.film(draw),
)

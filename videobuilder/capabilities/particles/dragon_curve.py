"""Dragon curve: a single segment folds again and again -- each time a copy of
the whole line swings 90 degrees about its far end -- until the path has
grown into the crinkled, self-avoiding dragon shape."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def dragon_unfold(progress, folds=10, ease=vb.ease_in_out_quart):
    """The dragon curve part-way through unfolding, as a point list in unit
    steps starting at (0, 0). `progress` (0 -> 1) runs through `folds`
    folds in turn; in each, a copy of the curve so far swings 90 degrees
    about its end point (eased by `ease`), so at 1 the path is the full
    order-`folds` dragon of 2**folds steps."""
    pts = [(0.0, 0.0), (1.0, 0.0)]
    done = vb.clamp01(progress) * folds
    for k in range(folds):
        t = vb.clamp01(done - k)
        if t <= 0:
            break
        a = math.pi / 2 * ease(t)
        ca, sa = math.cos(a), math.sin(a)
        ex, ey = pts[-1]
        swung = [(ex + (x - ex) * ca - (y - ey) * sa, ey + (x - ex) * sa + (y - ey) * ca)
                 for x, y in reversed(pts[:-1])]
        pts = pts + swung
    return pts


def dragon_steady(progress, folds=10, ease=vb.ease_in_out_quart):
    """`dragon_unfold`, turned and shrunk as it goes so the start stays at
    (0, 0) and each finished fold ends at (1, 0): the line seems to fold in
    place, the view easing through a 45-degree turn and a 1/sqrt(2) zoom
    per fold. Every point stays within about x -0.35..1.16,
    y -0.7..0.72."""
    pts = dragon_unfold(progress, folds, ease)
    done = vb.clamp01(progress) * folds
    k = min(int(done), folds)
    t = ease(done - k) if k < folds else 0.0
    turn, zoom = math.pi / 4 * (k + t), 2 ** (-(k + t) / 2)  # undoes the chord's (1 - i)**(k + t)
    ct, st = math.cos(turn) * zoom, math.sin(turn) * zoom
    return [(x * ct - y * st, x * st + y * ct) for x, y in pts]


def dragon_points(folds):
    """The finished order-`folds` dragon curve as a point list in unit steps."""
    return dragon_unfold(1.0, folds)


def fit(points, box, margin=0.0):
    """`points` scaled uniformly and centred to fit inside `box` (a vb.Box),
    leaving `margin` px on every side."""
    xs, ys = [x for x, _ in points], [y for _, y in points]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0 or 1e-9, max(ys) - y0 or 1e-9
    s = min((box.w - 2 * margin) / w, (box.h - 2 * margin) / h)
    ox = box.x + (box.w - w * s) / 2 - x0 * s
    oy = box.y + (box.h - h * s) / 2 - y0 * s
    return [(ox + x * s, oy + y * s) for x, y in points]


def _rgb(color):
    h = color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_dragon(cv, points, color, color_end=None, width=3, bands=24, alpha=1.0):
    """Stroke `points` (e.g. `fit(dragon_unfold(p), box)`), shading from
    `color` at the start to `color_end` (hex) at the end in `bands` steps,
    so the folds read as one continuous line."""
    if len(points) < 2:
        return
    if color_end is None:
        vb.paths.draw(cv, points, color, width=width, alpha=alpha)
        return
    a, b = _rgb(color), _rgb(color_end)
    n = len(points) - 1
    bands = max(1, min(bands, n))
    for i in range(bands):
        lo, hi = n * i // bands, n * (i + 1) // bands
        u = i / max(1, bands - 1)
        c = tuple(round(a[j] + (b[j] - a[j]) * u) for j in range(3))
        vb.paths.draw(cv, points[lo:hi + 1], c, width=width, alpha=alpha)


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.6)
    s = 330  # the chord in px; folding sweeps out about 1.5 x 1.42 chords
    x0, y0 = demo.W / 2 - 0.41 * s, demo.H / 2
    pts = [(x0 + x * s, y0 - y * s) for x, y in dragon_steady(p, 10)]
    draw_dragon(cv, pts, demo.ACCENT, demo.TEAL, width=max(1.5, 5 * (1 - p) ** 2))
    for (x, y), c in ((pts[0], demo.ACCENT), (pts[-1], demo.TEAL)):
        demo.dot(cv, x, y, 6, color=c)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('curve', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='dragon-curve',
    name='Dragon curve',
    family='particles',
    group='Fractals',
    aliases=('Heighway dragon', 'paper folding curve', 'Harter-Heighway dragon'),
    definition='A straight line keeps doubling by swinging a copy of itself a quarter turn around its end, '
               'until the right-angled path crinkles into a jagged dragon silhouette.',
    phrasings=('a line that keeps folding over on itself until it becomes a fractal dragon',
               'show the paper-folding fractal unfolding step by step',
               'a zigzag path that doubles each time and grows into a dragon shape'),
    related=('arc-bend-morph', 'spiral-expansion-draw', 'bezier-handle-bend', 'line-to-polygon-transform',
             'superformula-morph', 'bend-deformer'),
    api=('videobuilder.capabilities.particles.dragon_curve.dragon_unfold',
         'videobuilder.capabilities.particles.dragon_curve.dragon_steady',
         'videobuilder.capabilities.particles.dragon_curve.dragon_points',
         'videobuilder.capabilities.particles.dragon_curve.fit',
         'videobuilder.capabilities.particles.dragon_curve.draw_dragon'),
    demo=lambda: demo.film(draw),
)

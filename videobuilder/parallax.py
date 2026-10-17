"""Parallax: a scene of flat layers that slide at different speeds as the
camera pans, so it has depth. Each layer is one tile, drawn in code, repeated
side by side with no seam.

    from videobuilder import parallax, paths
    HILLS = parallax.ridge(720, 120, seed=2) + [(720, 300), (0, 300)]   # at import: one tile, closed
    def hills(cv, x):
        paths.draw(cv, [(x + px, 380 + py) for px, py in HILLS], '#2b3a4a', fill=True)
    LAYERS = (parallax.Layer(0.25, 720, hills), parallax.Layer(1.0, 240, ground_tile))
    parallax.draw(cv, LAYERS, camera_x)                 # far first, near last
"""
import math
import random
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Layer:
    """One flat layer: `draw(cv, x)` paints a single tile `width` px wide with
    its left edge at `x` (y in frame px), and the tile is repeated across the
    frame. Its right edge must meet its left edge, so the repeat has no seam.

    `depth` is how far it moves for each px the camera pans: 0 is pinned to
    the sky, 1 moves with the ground the character stands on, under 1 is
    further away and slower, over 1 is a foreground that passes in front,
    faster than the ground."""
    depth: float
    width: float
    draw: Callable


def offset(layer, camera_x):
    """Where the layer's first tile starts, in [-width, 0): the camera's pan
    times the layer's depth, wrapped to one tile."""
    return -((camera_x * layer.depth) % layer.width)


def draw(cv, layers, camera_x):
    """Draw `layers` back to front (list them far first) with the camera at
    `camera_x`, each tile repeated from just off the left edge to past the
    right one. A seamless loop: over the film, the camera's whole travel times
    each layer's depth comes to a whole number of that layer's tile widths."""
    for layer in layers:
        x = offset(layer, camera_x)
        while x < cv.width:
            layer.draw(cv, x)
            x += layer.width


def ridge(width, height, seed, bumps=(1, 2, 3), step=8):
    """One tile of a rolling skyline, as an open point list from x 0 to
    `width`, y from 0 (the highest crest) down to `height`: a few seeded
    waves that each fit a whole number of times in the tile (`bumps`), so
    its two ends meet and the tile repeats with no seam. Bake it in once at
    import. To fill it, close it down to the ground: `pts + [(width, h),
    (0, h)]`, shifted by the tile's x."""
    rnd = random.Random(seed)
    waves = [(k, rnd.uniform(0.4, 1.0) / k, rnd.uniform(0, 2 * math.pi)) for k in bumps]
    n = max(2, round(width / step))
    ys = [sum(a * math.sin(2 * math.pi * k * i / n + ph) for k, a, ph in waves) for i in range(n + 1)]
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or 1.0
    return [(width * i / n, height * (hi - y) / span) for i, y in enumerate(ys)]

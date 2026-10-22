"""Recursive rectangle subdivision: a rectangle is cut in two at a random
point, then one of its pieces is cut again, and so on, until the frame is a
patchwork of unequal blocks in a few flat colours."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

COLOURS = ('#e9e6df', demo.ACCENT, '#f2b45a', '#3a7bd5', demo.TEAL, '#e9e6df', '#2e3240')


def subdivide(x, y, w, h, splits=18, seed=0, min_size=70, lo=0.3, hi=0.7):
    """The cuts that split the box (x, y, w, h) into `splits + 1` blocks, in
    order, as `(parent, a, b, cut)`: `parent` is the box cut, `a` and `b` its
    two halves (left/top first), `cut` the dividing edge as `((x0, y0), (x1,
    y1))`. Each step picks a block, larger ones more often, and cuts its
    longer side at a random fraction between `lo` and `hi`; no piece ends up
    narrower than `min_size`. Stops early when nothing is left to cut. The
    same `seed` gives the same pattern."""
    rng = random.Random(seed)
    leaves, steps = [(x, y, w, h)], []
    for _ in range(splits):
        can = [r for r in leaves if max(r[2], r[3]) >= 2 * min_size]
        if not can:
            break
        r = rng.choices(can, weights=[bw * bh for _, _, bw, bh in can])[0]
        rx, ry, rw, rh = r
        across = rw > rh * 1.2 or (rw * 1.2 >= rh and rng.random() < 0.5)
        if rh < 2 * min_size or (rw >= 2 * min_size and across):
            t = min(max(rng.uniform(lo, hi), min_size / rw), 1 - min_size / rw)
            cx = rx + rw * t
            a, b, cut = (rx, ry, cx - rx, rh), (cx, ry, rx + rw - cx, rh), ((cx, ry), (cx, ry + rh))
        else:
            t = min(max(rng.uniform(lo, hi), min_size / rh), 1 - min_size / rh)
            cy = ry + rh * t
            a, b, cut = (rx, ry, rw, cy - ry), (rx, cy, rw, ry + rh - cy), ((rx, cy), (rx + rw, cy))
        leaves.remove(r)
        leaves += [a, b]
        steps.append((r, a, b, cut))
    return steps


def draw_rect_subdivision(cv, x, y, w, h, p, splits=18, seed=0, colours=COLOURS, line=demo.BG, width=8,
                          ease=vb.ease_in_out_quart, **kw):
    """Draw the box (x, y, w, h) subdividing at progress `p` (0 -> 1): the cuts
    of `subdivide` (`splits`, `seed` and `kw` go there) play one after another,
    each taking an equal share of `p`. A cut first draws across its block as a
    `line` of `width` px, then the second half fades to a fresh colour from
    `colours` while the first keeps its parent's. Returns the blocks on show
    (the one being cut still whole), as a list of boxes."""
    steps = subdivide(x, y, w, h, splits=splits, seed=seed, **kw)
    k = vb.clamp01(p) * len(steps)
    done = min(int(k), len(steps))
    q = k - done
    root = (x, y, w, h)
    fill, leaves = {root: colours[0]}, [root]
    for i, (r, a, b, _) in enumerate(steps):
        fill[a] = fill[r]
        fill[b] = random.Random(f'{seed}:{i}').choice([c for c in colours if c != fill[r]])
        if i < done:
            leaves.remove(r)
            leaves += [a, b]
    for r in leaves:
        cv.rect(*r, fill[r])
    if done < len(steps):
        _, _, b, ((x0, y0), (x1, y1)) = steps[done]
        grow, tint = ease(vb.clamp01(q / 0.55)), ease(vb.clamp01((q - 0.55) / 0.45))
        if tint > 0:
            cv.rect(*b, fill[b], alpha=tint)
        cv.line(x0, y0, x0 + (x1 - x0) * grow, y0 + (y1 - y0) * grow, line, width=width)
    for r in leaves:
        cv.outline(*r, line, width=width)
    return leaves


def draw(n, cv):
    w, h = 720, 440
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    p = demo.phase(n, 0.3, 2.7) ** 1.4  # the first, biggest cuts get the most time
    draw_rect_subdivision(cv, x, y, w, h, p, splits=20, seed=11, width=5, min_size=44)
    cv.mark('panel', x, y, w, h)


TECHNIQUE = Technique(
    id='recursive-rectangle-subdivision',
    name='Recursive rectangle subdivision',
    family='particles',
    group='Tiling & patterns',
    aliases=('BSP subdivision', 'Mondrian subdivision', 'binary space partition', 'rectangle split'),
    definition='One rectangle is cut in two at an off-centre point, and its pieces keep being cut '
               'the same way, until it has become a grid of blocks of every size.',
    phrasings=('keep slicing a box into smaller and smaller uneven boxes',
               'a Mondrian-style grid that builds itself one cut at a time',
               'split the panel at random, then split the halves again'),
    related=('polygon-subdivision', 'recursive-tree', 'shape-stacking-drop', 'diffusion-limited-aggregation',
             'koch-snowflake', 'bauhaus-geometric-shuffle'),
    api=('videobuilder.techniques.particles.recursive_rectangle_subdivision.draw_rect_subdivision',
         'videobuilder.techniques.particles.recursive_rectangle_subdivision.subdivide'),
    demo=lambda: demo.film(draw),
)

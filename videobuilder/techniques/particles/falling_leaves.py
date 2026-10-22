"""Falling leaves: a field of leaf shapes drifting down the frame, each
swaying side to side, rocking as it swings and flipping over as it tumbles."""
import math
import random

from ...canvas import rgba
from .. import _demo as demo
from ..schema import Technique

AUTUMN = ('#e8a33d', '#d9622b', '#f2c14e', '#b8452a', '#c98a2e')


def leaf(seed, i, t, w, h, size=(22, 44), fall=(90, 170), sway=(40, 110)):
    """Where leaf `i` of field `seed` is at `t` seconds in a `w` x `h` area, as
    `(x, y, size, angle, flip)`. Each leaf falls at its own speed, swings on
    a sine with its own width and period, rocks with the swing, spins slowly
    and flips (`flip` runs -1 -> 1: the leaf's width as it turns over). Leaves
    wrap from the bottom back to the top, so the field is full at every `t`
    and the same seed gives the same leaves, frame for frame."""
    r = random.Random(f'{seed}:{i}')
    s = r.uniform(*size)
    speed = r.uniform(*fall)
    span = h + 4 * s
    y = (r.uniform(0, span) + speed * t) % span - 2 * s
    swing = r.uniform(0.6, 1.3) * 2 * math.pi            # radians per second of the side-to-side swing
    ph = r.uniform(0, 2 * math.pi)
    x = r.uniform(0, w) + r.uniform(*sway) * math.sin(swing * t + ph)
    # rock with the swing (tilting into each turn), plus a slow spin of its own
    angle = r.uniform(0, 2 * math.pi) + 0.6 * math.cos(swing * t + ph) + r.uniform(-1.2, 1.2) * t
    flip = math.cos(r.uniform(1.5, 4.5) * t + r.uniform(0, 2 * math.pi))
    return x, y, s, angle, flip


def draw_leaf(cv, x, y, size, angle, flip, color, alpha=1.0):
    """One leaf centred at (x, y): a pointed oval `size` px long with a
    darker midrib, turned by `angle` radians and squashed across its width
    by `flip` (-1 -> 1; near 0 it is seen edge-on, below 0 its paler back)."""
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.rotate(angle)
    c.scale(max(abs(flip), 0.08), 1)
    half, wide = size / 2, size * 0.42
    c.new_path()
    c.move_to(0, -half)
    c.curve_to(wide, -half * 0.45, wide, half * 0.45, 0, half)
    c.curve_to(-wide, half * 0.45, -wide, -half * 0.45, 0, -half)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha * (1.0 if flip >= 0 else 0.72)))
    c.fill()
    c.move_to(0, -half * 0.8)
    c.line_to(0, half * 1.15)                              # the midrib runs on into a short stem
    c.set_source_rgba(0, 0, 0, 0.28 * alpha)
    c.set_line_width(max(size * 0.05, 1.0))
    c.stroke()
    c.restore()


def falling_leaves(cv, t, count=28, seed=0, box=None, colors=AUTUMN, alpha=1.0, **kw):
    """Draw a field of `count` leaves at `t` seconds, falling through `box`
    (x, y, w, h; default the whole frame). Leaf sizes vary, and the smaller
    ones are drawn first and fainter, so the field has some depth. `kw` goes
    to `leaf` (`size`, `fall`, `sway` ranges)."""
    bx, by, bw, bh = box or (0, 0, cv.width, cv.height)
    leaves = [(leaf(seed, i, t, bw, bh, **kw), colors[i % len(colors)]) for i in range(count)]
    lo, hi = kw.get('size', (22, 44))
    for (x, y, s, angle, flip), color in sorted(leaves, key=lambda e: e[0][2]):
        near = (s - lo) / ((hi - lo) or 1)
        draw_leaf(cv, bx + x, by + y, s, angle, flip, color, alpha * (0.6 + 0.4 * near))


def draw(n, cv):
    falling_leaves(cv, n / demo.FPS, count=30, seed=3, size=(34, 72))


TECHNIQUE = Technique(
    id='falling-leaves',
    name='Falling leaves',
    family='particles',
    group='Emitters',
    aliases=('autumn leaves', 'leaf fall'),
    definition='Leaf shapes drift down the frame, each swinging side to side and turning over as it '
               'tumbles, like leaves coming off a tree in a light breeze.',
    phrasings=('leaves floating down across the screen',
               'autumn leaves fluttering down in the background',
               'make it rain leaves that sway and spin as they fall'),
    related=('gravity-drop', 'momentum-fling', 'ball-bounce', 'falling-letter-rain', 'air-drag',
             'spiral-bloom'),
    api=('videobuilder.techniques.particles.falling_leaves.falling_leaves',
         'videobuilder.techniques.particles.falling_leaves.leaf',
         'videobuilder.techniques.particles.falling_leaves.draw_leaf'),
    demo=lambda: demo.film(draw),
)

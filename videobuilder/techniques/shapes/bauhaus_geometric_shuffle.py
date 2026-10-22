"""Bauhaus geometric shuffle: a handful of flat circles, squares and triangles
in primary colours hold a composition, then all slide and turn at once, a
little out of step, into a new one."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

RED, YELLOW, BLUE = '#e0402f', '#f2bf2c', '#2f5fd0'


def draw_shape(cv, kind, cx, cy, size, angle, color, alpha=1.0):
    """A flat `kind` ('circle', 'square' or 'triangle') centred at (cx, cy),
    `size` across, turned `angle` radians clockwise. A triangle is
    equilateral with its centroid at the centre."""
    c = cv.ctx
    r = size / 2
    if kind == 'circle':
        cv.sector(cx, cy, r, 0, 2 * math.pi, color, alpha=alpha)
        return
    c.save()
    c.translate(cx, cy)
    c.rotate(angle)
    c.new_path()
    if kind == 'square':
        c.rectangle(-r, -r, size, size)
    elif kind == 'triangle':
        R = size / math.sqrt(3)
        for i in range(3):
            a = -math.pi / 2 + i * 2 * math.pi / 3
            c.line_to(R * math.cos(a), R * math.sin(a))
        c.close_path()
    else:
        c.restore()
        raise ValueError(f'unknown shape kind {kind!r}')
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()
    c.restore()


def shuffle_poses(layouts, p, stagger=0.25, ease=vb.ease_in_out_quart):
    """Each shape's pose `(x, y, angle)` at progress `p` (0 -> 1) through
    `layouts`, a list of arrangements (each one pose per shape, same order).
    The moves between consecutive layouts share the progress evenly; within a
    move shape `i` starts `stagger` of the way later than shape 0 (spread
    across the set) and every shape lands together at the move's end."""
    moves = len(layouts) - 1
    if moves < 1:
        return list(layouts[0])
    at = vb.clamp01(p) * moves
    k = min(int(at), moves - 1)
    local = at - k
    a, b = layouts[k], layouts[k + 1]
    count = len(a)
    out = []
    for i, ((x0, y0, r0), (x1, y1, r1)) in enumerate(zip(a, b)):
        delay = stagger * i / max(1, count - 1)
        q = ease(vb.clamp01((local - delay) / (1 - delay)))
        out.append((x0 + (x1 - x0) * q, y0 + (y1 - y0) * q, r0 + (r1 - r0) * q))
    return out


def draw_shuffle(cv, shapes, layouts, p, **kw):
    """Draw `shapes` (each `(kind, size, color)`) at progress `p` through
    `layouts` (see `shuffle_poses`; `kw` goes there), in list order, so later
    shapes overlap earlier ones."""
    for (kind, size, color), (x, y, angle) in zip(shapes, shuffle_poses(layouts, p, **kw)):
        draw_shape(cv, kind, x, y, size, angle, color)
        cv.mark(kind, x - size / 2, y - size / 2, size, size)


U = demo.H / 720  # sizes and offsets below are for a 720-high frame
SHAPES = tuple((kind, size * U, color) for kind, size, color in (
    ('square', 210, BLUE),
    ('square', 190, demo.INK),
    ('circle', 170, YELLOW),
    ('circle', 140, RED),
    ('triangle', 200, RED),
    ('triangle', 180, BLUE),
))

T = math.pi / 6  # 30 degrees
LAYOUTS = [[(demo.W / 2 + dx * U, demo.H / 2 + dy * U, a) for dx, dy, a in layout] for layout in (
    [(-220, -60, 0.1), (30, 120, -0.15), (-330, 170, 0), (240, -170, 0), (300, 150, 0), (-60, -230, T)],
    [(210, 40, 0.1 + math.pi / 2), (-150, -140, -0.15 - math.pi / 2), (340, -190, 0), (-290, 190, 0),
     (-70, 200, 2 * T), (20, -40, -T)],
    [(-40, 30, 0.1 + math.pi), (230, -150, -0.15 - math.pi / 4), (-260, -170, 0), (160, 150, 0),
     (-330, 140, 4 * T), (340, 120, -3 * T)],
)]


def draw(n, cv):
    # hold, shuffle, hold, shuffle, hold
    first, second = demo.phase(n, 0.35, 1.25), demo.phase(n, 1.75, 2.65)
    draw_shuffle(cv, SHAPES, LAYOUTS, (first + second) / 2)


TECHNIQUE = Technique(
    id='bauhaus-geometric-shuffle',
    name='Bauhaus geometric shuffle',
    family='shapes',
    group='Geometric & Swiss style',
    aliases=('primary shape composition', 'constructivist shuffle', 'geometric collage motion'),
    definition='A few flat primary-coloured circles, squares and triangles glide and turn together '
               'from one arrangement into another, settling into a fresh composition each time.',
    phrasings=('red, yellow and blue shapes that slide around and rearrange themselves',
               'Bauhaus-style circles and triangles shuffling into new layouts',
               'simple geometric shapes that keep regrouping into a new composition'),
    related=('geometric-loop', 'tesseract-rotation', 'recursive-rectangle-subdivision', 'radial-repeater',
             'spin', 'tangram-rearrangement'),
    api=('videobuilder.techniques.shapes.bauhaus_geometric_shuffle.draw_shuffle',
         'videobuilder.techniques.shapes.bauhaus_geometric_shuffle.shuffle_poses',
         'videobuilder.techniques.shapes.bauhaus_geometric_shuffle.draw_shape'),
    demo=lambda: demo.film(draw),
)

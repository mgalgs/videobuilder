"""Particle Field Repel: a field of small dots drifts in place, and a pointer
moving through it pushes the dots aside, opening a gap that closes again
behind it as they ease back home."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

POINTER = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def field(box, cols, rows, jitter=0.3, seed=0):
    """Home positions of a `cols` x `rows` grid of dots spread over `box`
    (x, y, w, h), each nudged off its grid point by up to `jitter` of a cell
    so the field doesn't read as rigid. The same `seed` gives the same field."""
    x, y, w, h = box
    rnd = random.Random(seed)
    sx, sy = w / max(1, cols - 1), h / max(1, rows - 1)
    return [(x + i * sx + rnd.uniform(-jitter, jitter) * sx, y + j * sy + rnd.uniform(-jitter, jitter) * sy)
            for j in range(rows) for i in range(cols)]


def repel(points, pointer, t, radius=95, strength=1.0, settle=0.6, drift=4.0, seed=0, samples=12):
    """Where each home point in `points` sits at time `t` (seconds): drifting
    gently by up to `drift` px, and pushed out of the way by `pointer`, a
    function `t -> (x, y)` (or None while there is no pointer).

    A dot within `radius` of the pointer is shoved outward, nearly to the
    edge of that circle at `strength` 1. The push fades out over `settle`
    seconds once the pointer has passed, so a gap trails behind it and
    closes up -- the pointer's past is sampled `samples` times back across
    `settle`, and each dot takes its strongest push. Pure in `t`, so any
    frame renders on its own. Returns `(x, y, push)` per point, `push` 0 -> 1
    for how hard it is being displaced (useful to brighten pushed dots)."""
    past = []
    for k in range(samples + 1):
        age = settle * k / samples
        at = pointer(t - age) if t - age >= 0 else None
        if at is not None:
            past.append((at, (1 - age / settle) ** 2 if settle > 0 else 1.0))
        if settle <= 0:
            break
    out = []
    for i, (hx, hy) in enumerate(points):
        rnd = random.Random(f'{seed}:{i}')
        ph, fr = rnd.uniform(0, 2 * math.tau), rnd.uniform(0.5, 1.1)
        x = hx + drift * math.sin(fr * t * 1.7 + ph)
        y = hy + drift * math.cos(fr * t * 1.3 + ph * 1.3)
        best, bx, by = 0.0, 0.0, 0.0
        for (px, py), weight in past:
            dx, dy = x - px, y - py
            d = math.hypot(dx, dy)
            if d >= radius:
                continue
            fall = (1 - d / radius)
            m = radius * strength * fall ** 0.8 * weight * 0.9
            if m > best:
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                best, bx, by = m, dx / d * m, dy / d * m
        if past and past[0][1] == 1.0:  # nothing an older push left behind may sit inside the live gap
            (px, py), _ = past[0]
            dx, dy = x + bx - px, y + by - py
            d, edge = math.hypot(dx, dy), radius * strength * 0.9
            if 1e-6 < d < edge:
                bx, by = px + dx / d * edge - x, py + dy / d * edge - y
                best = max(best, edge - d)
        out.append((x + bx, y + by, min(1.0, best / (radius * 0.5))))
    return out


def draw_field(cv, dots, r=2.6, color=demo.MUTED, lit=demo.INK, alpha=0.8):
    """Draw `repel` output as small round dots: pushed dots grow a little and
    shift from `color` toward `lit`."""
    a, b = vb.rgba(color), vb.rgba(lit)
    for x, y, push in dots:
        c = '#' + ''.join(f'{round(255 * (a[k] + (b[k] - a[k]) * push)):02x}' for k in range(3))
        demo.dot(cv, x, y, r * (1 + 0.5 * push), c, alpha=alpha + (1 - alpha) * push)


def draw_pointer(cv, x, y, scale=1.0, color=demo.INK, edge=demo.BG):
    """An arrow mouse pointer with its tip at (x, y)."""
    pts = [(x + px * scale, y + py * scale) for px, py in POINTER]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(edge))
    c.set_line_width(2)
    c.stroke()


BOX = (90, 50, demo.W - 180, demo.H - 100)
HOME = field(BOX, 40, 22, seed=3)


def pointer_path(t):
    """The demo's pointer: in from the right edge, a wave across the field,
    and out at the left, leaving half a second for the dots to settle."""
    p = vb.clamp01((t - 0.3) / 2.1)
    p = 0.5 * p + 0.5 * p * p * (3 - 2 * p)
    return (demo.W + 60 - (demo.W + 120) * p, demo.H / 2 + 20 + 130 * math.sin(p * 2 * math.pi + 0.4))


def draw(n, cv):
    t = n / demo.FPS
    draw_field(cv, repel(HOME, pointer_path, t, seed=3))
    draw_pointer(cv, *pointer_path(t))
    cv.mark('field', *BOX)


TECHNIQUE = Technique(
    id='particle-field-repel',
    name='Particle field repel',
    family='ui',
    group='Cursor & hover',
    aliases=('interactive particles', 'cursor repel', 'repulsor field', 'radial push'),
    definition='A pointer moving through a softly drifting field of dots shoves the nearby ones aside, '
               'and they glide back into place once it has passed.',
    phrasings=('dots that scatter away from the mouse and then float back',
               'the cursor pushes a hole through a grid of particles',
               'particles that flee the pointer as it moves across them'),
    related=('dot-grid-displacement', 'flow-field', 'spring-drag-letters', 'cursor-path-animation',
             'wind-field', 'proximity-stagger'),
    api=('videobuilder.techniques.ui.particle_field_repel.repel',
         'videobuilder.techniques.ui.particle_field_repel.field',
         'videobuilder.techniques.ui.particle_field_repel.draw_field',
         'videobuilder.techniques.ui.particle_field_repel.draw_pointer'),
    demo=lambda: demo.film(draw),
)

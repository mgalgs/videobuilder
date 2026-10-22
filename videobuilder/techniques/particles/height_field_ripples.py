"""Height-field ripples: a grid of water heights stepped by the wave equation.
Drops push dents into the surface, the dents spread as rings, bounce off the
walls of the pool and cross each other, and the surface slowly calms."""
from functools import lru_cache

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba


class HeightField:
    """A `cols` x `rows` grid of surface heights with the previous step kept,
    advanced by the discrete wave equation. The edges mirror their
    neighbours, so a wave reaching a wall reflects back into the pool.
    `damping` (just under 1) is how much of the motion survives each step."""

    def __init__(self, cols=48, rows=48, damping=0.985):
        self.cols, self.rows, self.damping = cols, rows, damping
        self.h = [0.0] * (cols * rows)
        self.prev = [0.0] * (cols * rows)

    def drop(self, x, y, depth=1.0, radius=3.0):
        """Push a round dent `depth` deep into the surface at grid point
        (x, y) (fractions of a cell are fine), easing out over `radius` cells."""
        c, r = self.cols, self.rows
        reach = int(radius) + 1
        for j in range(max(0, int(y) - reach), min(r, int(y) + reach + 2)):
            for i in range(max(0, int(x) - reach), min(c, int(x) + reach + 2)):
                d2 = ((i - x) ** 2 + (j - y) ** 2) / (radius * radius)
                if d2 < 1:
                    dent = depth * (1 - d2) ** 2
                    self.h[j * c + i] -= dent
                    self.prev[j * c + i] -= dent  # starts at rest, so it springs back rather than plunges

    def step(self):
        """Advance one time step: each cell moves toward the mean of its four
        neighbours with the velocity it already had."""
        c, r, h, prev, k = self.cols, self.rows, self.h, self.prev, self.damping
        new = [0.0] * (c * r)
        for j in range(r):
            up = (j - 1 if j else 1) * c          # mirrored edges reflect the waves
            dn = (j + 1 if j < r - 1 else r - 2) * c
            row = j * c
            for i in range(c):
                lf = i - 1 if i else 1
                rt = i + 1 if i < c - 1 else c - 2
                s = h[row + lf] + h[row + rt] + h[up + i] + h[dn + i]
                new[row + i] = (s * 0.5 - prev[row + i]) * k
        self.prev, self.h = h, new


@lru_cache(maxsize=4)
def ripple_frames(drops, frames, cols=48, rows=48, steps_per_frame=2, damping=0.985):
    """The height grid for every frame of a shot, as a tuple of flat lists.
    `drops` is a tuple of `(frame, x, y, depth, radius)`, x and y in cells;
    each lands at the start of its frame. Cached, so a film can ask for any
    frame in any order and the simulation runs once."""
    hf = HeightField(cols, rows, damping)
    pending = sorted(drops)
    out = []
    for n in range(frames):
        while pending and pending[0][0] <= n:
            _, x, y, depth, radius = pending.pop(0)
            hf.drop(x, y, depth, radius)
        out.append(tuple(hf.h))
        for _ in range(steps_per_frame):
            hf.step()
    return tuple(out)


def draw_height_field(cv, heights, cols, rows, cx, cy, size=620, lift=40.0, color=demo.TEAL,
                      light=(-0.6, -1.0), grid=True):
    """Draw a flat list of `cols` x `rows` heights as a shaded isometric
    surface: a diamond `size` px wide centred on (cx, cy), each unit of
    height raising a point `lift` px. Facets are lit from `light` (a slope
    direction), so crests catch light and troughs fall dark; `grid` draws
    the faint mesh lines across the facets."""
    ctx = cv.ctx
    sx = size / 2 / (cols - 1)
    sy = sx * 0.5
    ox, oy = cx, cy - (rows - 1 + cols - 1) * sy / 2
    r, g, b, _ = rgba(color)
    lx, ly = light

    def pt(i, j):
        return ox + (i - j) * sx, oy + (i + j) * sy - heights[j * cols + i] * lift

    for d in range(cols + rows - 3):              # back to front, so nearer facets cover farther ones
        for j in range(max(0, d - (cols - 2)), min(rows - 1, d + 1)):
            i = d - j
            h00, h10 = heights[j * cols + i], heights[j * cols + i + 1]
            h01, h11 = heights[(j + 1) * cols + i], heights[(j + 1) * cols + i + 1]
            gx, gy = (h10 + h11 - h00 - h01) * 0.5, (h01 + h11 - h00 - h10) * 0.5
            shade = max(0.25, min(1.6, 0.85 + 2.2 * (gx * lx + gy * ly)))
            ctx.move_to(*pt(i, j))
            ctx.line_to(*pt(i + 1, j))
            ctx.line_to(*pt(i + 1, j + 1))
            ctx.line_to(*pt(i, j + 1))
            ctx.close_path()
            ctx.set_source_rgb(min(1, r * shade), min(1, g * shade), min(1, b * shade))
            if grid:
                ctx.fill_preserve()
                ctx.set_source_rgba(0, 0, 0, 0.12)
                ctx.set_line_width(0.8)
                ctx.stroke()
            else:
                ctx.fill()
    # the pool's rim: the four outer edges, following the surface
    for edge in (((i, 0) for i in range(cols)), ((cols - 1, j) for j in range(rows)),
                 ((i, rows - 1) for i in range(cols - 1, -1, -1)), ((0, j) for j in range(rows - 1, -1, -1))):
        pts = [pt(i, j) for i, j in edge]
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
    ctx.set_source_rgba(min(1, r * 1.3), min(1, g * 1.3), min(1, b * 1.3), 0.9)
    ctx.set_line_width(2)
    ctx.stroke()


N = 44
DROPS = ((4, 16.0, 14.0, 1.6, 4.0), (40, 29.0, 30.0, 1.4, 3.5), (64, 11.0, 31.0, 1.2, 3.0))


def draw(n, cv):
    frames = ripple_frames(DROPS, round(demo.SECONDS * demo.FPS), N, N, steps_per_frame=1, damping=0.992)
    draw_height_field(cv, frames[min(n, len(frames) - 1)], N, N, demo.W / 2, demo.H / 2 + 10, size=760,
                      lift=26)
    cv.mark('pool', demo.W / 2 - 380, demo.H / 2 - 180, 760, 380)


TECHNIQUE = Technique(
    id='height-field-ripples',
    name='Height-field ripples',
    family='particles',
    group='Water & light',
    aliases=('wave equation ripples', 'water ripples', 'ripple tank', 'water surface simulation'),
    definition='A surface made of a grid of heights is simulated as water, so each drop dents it into '
               'rings that spread, bounce back off the edges and cross one another before settling.',
    phrasings=('drip some drops into a pool and let the waves bounce around',
               'a water surface that ripples out from where things land',
               'simulate a little pond with waves reflecting off its walls'),
    related=('ripple', 'ripple-rings', 'ripple-displacement', 'wave-deformer', 'refraction-ripple',
             'ridgeline-ripple'),
    api=('videobuilder.techniques.particles.height_field_ripples.HeightField',
         'videobuilder.techniques.particles.height_field_ripples.ripple_frames',
         'videobuilder.techniques.particles.height_field_ripples.draw_height_field'),
    demo=lambda: demo.film(draw),
)

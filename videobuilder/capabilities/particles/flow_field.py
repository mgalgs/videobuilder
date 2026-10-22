"""Flow Field: every point of the frame carries a direction read from smooth
noise, and a crowd of particles drifts along those directions, their trailing
streaks bending together into currents that draw the field itself."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..typography.noise_field_warp import Noise


class FlowField:
    """A still vector field: at film point (x, y) the heading is smooth noise
    of feature `size` px, scaled to `turns` full turns, so nearby points point
    nearly the same way and the field reads as broad, curving currents. The
    same `seed` gives the same field."""

    def __init__(self, seed=0, size=520.0, turns=1.2, octaves=2):
        self.noise = Noise(f'flow:{seed}')
        self.size, self.turns, self.octaves = size, turns, octaves
        self._lines = {}

    def angle(self, x, y):
        """The heading in radians at (x, y), canvas convention (clockwise from +x)."""
        return self.noise.fbm(x / self.size, y / self.size, self.octaves) * self.turns * 2 * math.pi

    def streamline(self, x, y, steps, step=6.0):
        """`steps + 1` points from (x, y) following the field, `step` px apart."""
        pts = [(x, y)]
        for _ in range(steps):
            a = self.angle(x, y)
            x, y = x + step * math.cos(a), y + step * math.sin(a)
            pts.append((x, y))
        return pts

    def _line(self, key, x, y, steps, step):
        # Streamlines are extended lazily and kept, so rendering frame n never re-traces 0..n-1.
        pts = self._lines.get(key)
        if pts is None:
            pts = self._lines[key] = [(x, y)]
        if len(pts) <= steps:
            pts.extend(self.streamline(*pts[-1], steps - len(pts) + 1, step)[1:])
        return pts


def flow_trails(field, box, t, count=700, speed=160.0, trail=120.0, life=2.4, step=6.0, seed=0):
    """The particles of `field` inside `box` at time `t` seconds, as
    `(points, fade, i)` triples: `points` is particle `i`'s streak, head last,
    at most `trail` px long; `fade` (0 -> 1) eases it in after it spawns and
    out before it dies. Each particle moves `speed` px a second, lives `life`
    seconds from a random spot, then respawns elsewhere; lifetimes are
    staggered so the crowd stays even. Deterministic in `seed`, so frames can
    render in any order."""
    out = []
    per_sec = speed / step
    for i in range(count):
        rnd = random.Random(f'{seed}:{i}')
        clock = t + rnd.uniform(0, life)
        cycle = math.floor(clock / life)
        age = clock - cycle * life
        spawn = random.Random(f'{seed}:{i}:{cycle}')
        x0, y0 = box.x + spawn.uniform(0, box.w), box.y + spawn.uniform(0, box.h)
        head = age * per_sec
        tail = max(0.0, head - trail / step)
        pts = field._line((seed, i, cycle), x0, y0, math.ceil(head), step)
        k0, k1 = int(tail), int(head)
        streak = pts[k0:k1 + 1]
        f = head - k1  # sub-step head, so motion is smooth between samples
        if f > 0 and k1 + 1 < len(pts):
            (ax, ay), (bx, by) = pts[k1], pts[k1 + 1]
            streak.append((ax + (bx - ax) * f, ay + (by - ay) * f))
        if len(streak) >= 2:
            out.append((streak, min(1.0, age / 0.35, (life - age) / 0.35), i))
    return out


def draw_flow_field(cv, box, t, field=None, colors=(demo.TEAL, demo.ACCENT, demo.INK), width=1.6,
                    alpha=0.8, **kw):
    """Draw a flow field's particle streaks inside `box` at time `t`, clipped
    to it: each streak fades from clear at its tail to `alpha` at its head,
    coloured from `colors` by particle. `field` defaults to `FlowField()`;
    pass one to keep its streamline cache across frames. `kw` goes to
    `flow_trails` (`count`, `speed`, `trail`, `life`, `seed`)."""
    field = field or FlowField()
    c = cv.ctx
    with cv.clip(box.x, box.y, box.w, box.h):
        c.set_line_width(width)
        c.set_line_cap(1)  # round
        for pts, fade, i in flow_trails(field, box, t, **kw):
            r, g, b, _ = vb.rgba(colors[i % len(colors)], 1.0)
            n = len(pts)
            bands = min(4, n - 1)
            for j in range(bands):
                a, z = j * (n - 1) // bands, (j + 1) * (n - 1) // bands
                c.move_to(*pts[a])
                for p in pts[a + 1:z + 1]:
                    c.line_to(*p)
                c.set_source_rgba(r, g, b, alpha * fade * (j + 1) / bands)
                c.stroke()


BOX = vb.Box(150, 70, demo.W - 300, demo.H - 140)
FIELD = FlowField(seed=3)


def draw(n, cv):
    t = n / demo.FPS
    cv.rect(BOX.x, BOX.y, BOX.w, BOX.h, '#0b0d12', radius=12)
    grow = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.4))
    draw_flow_field(cv, BOX, t, field=FIELD, count=900, trail=30 + 230 * grow, speed=170, life=2.6,
                    colors=(demo.TEAL, demo.ACCENT, '#8f9cff'), seed=3)
    cv.mark('field', BOX.x, BOX.y, BOX.w, BOX.h)


TECHNIQUE = Technique(
    id='flow-field',
    name='Flow field',
    family='particles',
    group='Noise & fields',
    aliases=('vector field particles', 'angle field', 'noise flow', 'flow lines'),
    definition='Thousands of particles drift along a hidden map of directions, and the streaks they '
               'leave bend together into smooth currents that reveal the shape of the field.',
    phrasings=('particles streaming along invisible swirling currents',
               'lots of little lines that flow and curl like wind or water',
               'generative hair-like strokes following a noise field'),
    related=('wind-field', 'turbulence-displacement', 'starfield', 'particle-morph', 'particle-field-repel',
             'flow-map-lines'),
    api=('videobuilder.techniques.particles.flow_field.draw_flow_field',
         'videobuilder.techniques.particles.flow_field.FlowField',
         'videobuilder.techniques.particles.flow_field.flow_trails'),
    demo=lambda: demo.film(draw),
)

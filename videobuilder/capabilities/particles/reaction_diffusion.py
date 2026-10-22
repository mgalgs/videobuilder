"""Reaction-diffusion: a Gray-Scott simulation of two chemicals on a grid.
A few seeded spots of the second chemical feed on the first, spread, split
and curl into worms until a maze-like pattern covers the whole surface."""
import random

import videobuilder as vb
from PIL import Image

from .. import _demo as demo
from ..schema import Capability

_SIMS = {}  # the arguments of reaction_diffusion -> _Sim, so frames share one run
CHECKPOINT = 100  # steps between saved states, so going back in time never restarts from zero


def _scatter(count, spread, w, h, rnd):
    """`count` (x, y) fractions around the centre, within `spread` of the
    width of it, kept far enough apart that each starts as its own dot."""
    out, gap = [], 10
    for _ in range(count * 200):
        if len(out) == count:
            break
        x, y = w / 2 + rnd.uniform(-1, 1) * spread * w, h / 2 + rnd.uniform(-1, 1) * spread * w
        if (x - w / 2) ** 2 + (y - h / 2) ** 2 <= (spread * w) ** 2 and \
                all((x - a) ** 2 + (y - b) ** 2 >= gap ** 2 for a, b in out):
            out.append((x, y))
    return [(x / w, y / h) for x, y in out]


class _Sim:
    """One Gray-Scott run on a `w` x `h` torus. `u` is the chemical being
    eaten (starts at 1 everywhere), `v` the one growing (starts only in the
    seeds). Steps forward from the nearest saved state on demand."""

    def __init__(self, w, h, feed, kill, du, dv, seeds, spread, seed):
        self.w, self.h = w, h
        self.feed, self.kill, self.du, self.dv = feed, kill, du, dv
        u, v = [1.0] * (w * h), [0.0] * (w * h)
        rnd = random.Random(seed)
        if isinstance(seeds, int):
            seeds = _scatter(seeds, spread, w, h, rnd)
        for fx, fy in seeds:
            cx, cy = int(fx * w), int(fy * h)
            for y in range(cy - 2, cy + 3):
                for x in range(cx - 2, cx + 3):
                    i = (y % h) * w + x % w
                    u[i], v[i] = 0.5, 0.25
        self.saved = {0: (u, v)}
        self.at, self.u, self.v = 0, u, v
        self.fields = {}  # step -> 'L' image of v

    def _run(self, steps):
        w, f, fk, du, dv = self.w, self.feed, self.feed + self.kill, self.du, self.dv
        u, v = self.u, self.v
        for _ in range(steps):
            # Neighbours by shifting the flat grid; the 5-point Laplacian is p + q + r + s - 4a.
            ul, ur, uu, ud = u[1:] + u[:1], u[-1:] + u[:-1], u[w:] + u[:w], u[-w:] + u[:-w]
            vl, vr, vu, vd = v[1:] + v[:1], v[-1:] + v[:-1], v[w:] + v[:w], v[-w:] + v[:-w]
            uvv = [a * b * b for a, b in zip(u, v)]
            u = [a + du * (p + q + r + s - 4 * a) - x + f * (1 - a) for a, p, q, r, s, x in zip(u, ul, ur, uu, ud, uvv)]
            v = [b + dv * (p + q + r + s - 4 * b) + x - fk * b for b, p, q, r, s, x in zip(v, vl, vr, vu, vd, uvv)]
            self.at += 1
            if self.at % CHECKPOINT == 0:
                self.saved[self.at] = (u, v)
        self.u, self.v = u, v

    def field(self, step):
        if step not in self.fields:
            if step < self.at:
                self.at = max(s for s in self.saved if s <= step)
                self.u, self.v = self.saved[self.at]
            self._run(step - self.at)
            self.fields[step] = Image.frombytes('L', (self.w, self.h),
                                                bytes(min(255, int(b * 730)) for b in self.v))
        return self.fields[step]


def reaction_diffusion(steps, width=96, height=54, feed=0.029, kill=0.057, du=0.13, dv=0.065,
                       seeds=12, spread=0.1, seed=0):
    """The pattern after `steps` steps of a Gray-Scott reaction-diffusion run,
    as a `width` x `height` PIL 'L' image (bright where the growing chemical
    is). `feed`/`kill` pick the pattern: the default grows a maze of worms;
    about (0.0545, 0.062) gives coral, (0.037, 0.06) fingerprints, and
    (0.026, 0.055) splits into spots and stripes. `du`/`dv` are the two
    diffusion rates (smaller gives finer features, but spreads slower).
    `seeds` is a count of spots scattered around the centre (`spread` is
    their spread as a fraction of the width), or a list of (x, y) fractions
    of the grid. The grid wraps at its edges, so the pattern tiles.

    About 1300 steps fill the default grid from a central cluster; one run is
    shared by every call with the same arguments, so ask for frame `n` as
    `steps = start + n * per_frame` in any order. Pure Python: roughly 2-3
    seconds per 1000 steps on the default grid."""
    key = (width, height, feed, kill, du, dv, seeds if isinstance(seeds, int) else tuple(seeds), spread, seed)
    if key not in _SIMS:
        _SIMS[key] = _Sim(width, height, feed, kill, du, dv, key[6], spread, seed)
    return _SIMS[key].field(int(steps))


def _ramp(stops):
    """A 256-entry lookup per channel through `stops`, (level 0-1, colour) pairs."""
    stops = [(t, vb.canvas.rgba(c)) for t, c in stops]
    out = [], [], []
    for i in range(256):
        t = i / 255
        j = max(k for k in range(len(stops)) if stops[k][0] <= t) if t >= stops[0][0] else 0
        t0, c0 = stops[j]
        t1, c1 = stops[min(j + 1, len(stops) - 1)]
        s = 0 if t1 == t0 else vb.clamp01((t - t0) / (t1 - t0))
        s = s * s * (3 - 2 * s)
        for ch in range(3):
            out[ch].append(round(255 * (c0[ch] + (c1[ch] - c0[ch]) * s)))
    return out


def draw_reaction_diffusion(cv, field, x, y, w, h, colors=(demo.BG, demo.TEAL, demo.ACCENT), alpha=1.0):
    """Draw a `reaction_diffusion` field stretched over the box (x, y, w, h),
    smoothed up to the frame's resolution and coloured through `colors`:
    (empty, edge glow, pattern). Returns the Box."""
    px = max(1, round(w * cv.scale_factor())), max(1, round(h * cv.scale_factor()))
    big = field.resize(px, Image.BICUBIC)
    lut = _ramp(((0.0, colors[0]), (0.4, colors[0]), (0.55, colors[1]), (0.7, colors[2]), (1.0, colors[2])))
    rgb = Image.merge('RGB', [big.point(lut[ch]) for ch in range(3)])
    cv.image(vb.canvas.Image.from_pil(rgb), x, y, w, h, alpha=alpha)
    return vb.Box(x, y, w, h)


START, PER_FRAME = 20, 15  # steps before the first frame (the seeds show as dots), steps per frame


def draw(n, cv):
    field = reaction_diffusion(START + n * PER_FRAME, seeds=14, spread=0.18, seed=4)
    box = draw_reaction_diffusion(cv, field, 0, 0, demo.W, demo.H)
    cv.mark('pattern', *box)


CAPABILITY = Capability(
    id='reaction-diffusion',
    name='Reaction-diffusion',
    family='particles',
    group='Reaction & growth',
    aliases=('Gray-Scott', 'Turing patterns', 'reaction diffusion'),
    definition='A few dots grow, split and curl into worm-like stripes that keep spreading until an '
               'organic maze pattern covers the frame.',
    phrasings=('an organic pattern that grows like coral or a fingerprint across the screen',
               'spots that multiply and turn into a squiggly maze',
               'animal-skin stripes forming by themselves'),
    related=('ink-in-water', 'brian-s-brain', 'fractal-brownian-motion', 'dissolve-to-particles',
             'ink-splash-spread', 'particle-life'),
    api=('videobuilder.capabilities.particles.reaction_diffusion.reaction_diffusion',
         'videobuilder.capabilities.particles.reaction_diffusion.draw_reaction_diffusion'),
    demo=lambda: demo.film(draw),
)

"""Rainfall: many thin streaks fall at a slight slant across the frame, in a
few depth layers (far ones fainter, shorter and slower), and drops that hit
the ground burst into small splashes."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _drops(w, floor_y, count, speed, slant, layers, seed):
    """Each drop's fixed traits: `(x, depth, v, length, span, offset)`."""
    rng = random.Random(seed)
    for i in range(count):
        depth = min((i % layers + rng.random() * 0.5) / max(layers - 0.5, 1), 1.0)
        v = speed * (0.45 + 0.55 * depth)
        length = 30 + 60 * depth
        span = floor_y + length
        offset = rng.random() * span
        x = rng.random() * (w + slant * span) - slant * span
        yield x, depth, v, length, span, offset


def raindrops(t, w, h, count=220, speed=1400, slant=0.18, layers=3, seed=0, ground=None):
    """The rain at `t` seconds over a `w` x `h` frame, as dicts with the
    streak `x0, y0, x1, y1` (top to bottom), its `depth` (0 far -> 1 near)
    and `length`. Each drop loops forever on its own phase, so the field is
    full from the first frame. Near drops fall at `speed` px/s; `slant` is
    the sideways drift per pixel fallen. Drops stop at `ground` (default:
    the frame's bottom). The same `seed` gives the same rain."""
    floor_y = h if ground is None else ground
    out = []
    for x, depth, v, length, span, offset in _drops(w, floor_y, count, speed, slant, layers, seed):
        fall = (offset + v * t) % span
        y0, y1 = fall - length, min(fall, floor_y)
        out.append(dict(x0=x + slant * y0, y0=y0, x1=x + slant * y1, y1=y1, depth=depth, length=length))
    return out


def splashes(t, w, h, count=220, speed=1400, slant=0.18, layers=3, seed=0, ground=None, life=0.28):
    """Where the drops of `raindrops` (same arguments) last met the ground,
    within `life` seconds of `t`: dicts with `x`, `y`, `depth` and `age`
    (0 -> 1 across `life`). Only the nearer half of the drops splash."""
    floor_y = h if ground is None else ground
    out = []
    for x, depth, v, length, span, offset in _drops(w, floor_y, count, speed, slant, layers, seed):
        since = ((offset + v * t) % span - floor_y) / v   # seconds since the head hit the ground
        if depth >= 0.5 and 0 <= since < life:
            out.append(dict(x=x + slant * floor_y, y=floor_y, depth=depth, age=since / life))
    return out


def draw_rain(cv, t, w=None, h=None, color=demo.INK, alpha=0.7, width=3, ground=None, splash=True, **kw):
    """Draw rain at `t` seconds over the whole canvas (or `w` x `h`): far
    streaks thin and faint, near ones bold, and, when `ground` is given and
    `splash` is on, a little crown and ripple where each near drop lands.
    `kw` goes to `raindrops` (`count`, `speed`, `slant`, `layers`, `seed`)."""
    w = demo.W if w is None else w
    h = demo.H if h is None else h
    for d in raindrops(t, w, h, ground=ground, **kw):
        if d['y1'] <= d['y0']:
            continue
        k = d['depth']
        cv.line(d['x0'], d['y0'], d['x1'], d['y1'], color, width=width * (0.35 + 0.65 * k),
                alpha=alpha * (0.25 + 0.75 * k))
    if ground is None or not splash:
        return
    for s in splashes(t, w, h, ground=ground, **kw):
        a, k = s['age'], s['depth']
        fade = alpha * (1 - a) * k
        r = (8 + 34 * a) * k
        c = cv.ctx                                   # a flat ripple: a circle squashed to an ellipse
        c.save()
        c.translate(s['x'], s['y'])
        c.scale(1, 0.22)
        c.new_path()
        c.arc(0, 0, r, 0, 2 * math.pi)
        c.restore()
        c.set_source_rgba(*vb.rgba(color, fade))
        c.set_line_width(width * 0.6)
        c.stroke()
        rise = 26 * k * math.sin(math.pi * min(a * 1.4, 1))
        for side in (-1, 1):                         # two droplets flick up and out
            demo.dot(cv, s['x'] + side * (6 + 22 * a) * k, s['y'] - rise, r=2.6 * k, color=color, alpha=fade)


GROUND = demo.H - 170


def draw(n, cv):
    t = n / demo.FPS
    cv.fill('#11151d')
    demo.floor(cv, GROUND, color=demo.LINE)
    p = demo.phase(n, 0.0, 0.6)                      # the shower thickens in, then holds
    draw_rain(cv, t, color='#cfe0f0', alpha=0.85 * p + 0.15, ground=GROUND,
              count=int(60 + 180 * p), seed=4)
    cv.mark('rain', 0, 0, demo.W, GROUND)


TECHNIQUE = Technique(
    id='rainfall',
    name='Rainfall',
    family='particles',
    group='Emitters',
    aliases=('rain', 'rain effect', 'rain particles', 'rain shower'),
    definition='Thin slanted streaks pour down the frame in layers of depth, the nearer ones brighter '
               'and faster, splashing where they strike the ground.',
    phrasings=('make it rain over the scene',
               'add falling rain streaks with little splashes on the floor',
               'a rainy-weather overlay of drops coming down'),
    related=('rain-on-glass', 'falling-letter-rain', 'falling-glyph-rain-reveal', 'matrix-digital-rain',
             'drip-wipe', 'ripple'),
    api=('videobuilder.techniques.particles.rainfall.draw_rain',
         'videobuilder.techniques.particles.rainfall.raindrops',
         'videobuilder.techniques.particles.rainfall.splashes'),
    demo=lambda: demo.film(draw),
)

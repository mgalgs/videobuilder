"""Confetti: small flat paper pieces drift down the frame, swaying side to
side and tumbling end over end, so each one flashes wide and then thins to an
edge as it turns."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

COLORS = (demo.ACCENT, demo.TEAL, demo.INK, '#f2c14e', '#8c7ae6')


def confetti(t, width, height, count=140, seed=0, fall=(170, 290), size=(10, 18), lead=0.8):
    """The confetti at `t` seconds as a list of pieces, each a dict with the
    centre `x`, `y`, the in-plane `angle` (radians), `flip` (-1..1, the
    cosine of its tumble: +-1 shows the full face, 0 is edge-on), its `w` and
    `h` and a `color` index into the palette. Pieces start scattered up to
    `lead` frame-heights above the top and fall at a speed from `fall`
    (px/s), so the frame fills from the top; a piece that leaves the bottom
    re-enters above. The same `seed` gives the same shower, frame for frame."""
    rnd = random.Random(seed)
    out = []
    span = height * (1 + lead) + 40
    for i in range(count):
        x0 = rnd.uniform(-0.05, 1.05) * width
        y0 = -rnd.uniform(0.02, lead) * height
        speed = rnd.uniform(*fall)
        sway, sway_hz, sway_ph = rnd.uniform(10, 40), rnd.uniform(0.3, 0.9), rnd.uniform(0, 2 * math.pi)
        spin, angle0 = rnd.uniform(-2.5, 2.5), rnd.uniform(0, 2 * math.pi)
        tumble, tumble0 = rnd.uniform(4, 10) * rnd.choice((-1, 1)), rnd.uniform(0, 2 * math.pi)
        w = rnd.uniform(*size)
        h = w * rnd.uniform(0.45, 0.7)
        color = rnd.randrange(1 << 16)
        y = y0 + speed * t
        if y > height + 30:  # wrap round, so a long shot keeps raining
            y = (y + height * lead + 20) % span - height * lead - 20
        out.append(dict(x=x0 + sway * math.sin(2 * math.pi * sway_hz * t + sway_ph), y=y,
                        angle=angle0 + spin * t, flip=math.cos(tumble0 + tumble * t),
                        w=w, h=h, color=color))
    return out


def draw_piece(cv, x, y, w, h, angle, flip, color, alpha=1.0):
    """One confetti piece: a `w` x `h` rectangle at (x, y), turned `angle`
    in the frame and squashed across its height by `flip` (the tumble), its
    back face (flip < 0) and edge-on turns drawn darker, as if lit from the front."""
    shade = 0.45 + 0.55 * abs(flip) if flip >= 0 else 0.3 + 0.4 * abs(flip)
    r, g, b, a = vb.rgba(color)
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.rotate(angle)
    c.scale(1, max(abs(flip), 0.08))
    c.rectangle(-w / 2, -h / 2, w, h)
    c.restore()
    c.set_source_rgba(r * shade, g * shade, b * shade, a * alpha)
    c.fill()


def draw_confetti(cv, t, colors=COLORS, alpha=1.0, **kw):
    """Draw the confetti shower at `t` seconds over the whole canvas, pieces
    coloured from `colors`. `kw` goes to `confetti` (count, seed, fall, size,
    lead). Returns the pieces drawn."""
    pieces = confetti(t, cv.width, cv.height, **kw)
    for p in pieces:
        draw_piece(cv, p['x'], p['y'], p['w'], p['h'], p['angle'], p['flip'],
                   colors[p['color'] % len(colors)], alpha=alpha)
    return pieces


def draw(n, cv):
    draw_confetti(cv, n / demo.FPS, count=170, seed=3)
    cv.mark('confetti', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='confetti',
    name='Confetti',
    family='particles',
    group='Emitters',
    aliases=('paper confetti', 'tumbling flakes', 'confetti rain'),
    definition='Little flat paper pieces in a few colours drift down the screen, swaying and turning '
               'over so each one flickers between its full face and a thin edge.',
    phrasings=('make confetti fall over the whole screen',
               'a shower of colourful paper bits tumbling down',
               'rain some celebration confetti from the top'),
    related=('confetti-burst', 'circle-pop', 'crumple', 'twist-deformer', 'character-3d-flip', 'tile-flip'),
    api=('videobuilder.capabilities.particles.confetti.draw_confetti',
         'videobuilder.capabilities.particles.confetti.confetti',
         'videobuilder.capabilities.particles.confetti.draw_piece'),
    demo=lambda: demo.film(draw),
)

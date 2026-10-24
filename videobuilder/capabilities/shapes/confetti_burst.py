"""Confetti Burst: the same idea as Confetti (`../particles/confetti.py`,
which keeps the capability) -- both show coloured paper pieces flipping and
fluttering through the air; this one only adds the upward launch a fistful
of them gets before gravity takes over. This module's own code stays (a
film may still import it), but it is no longer a capability of its own."""
import math
import random

from .. import _demo as demo

MERGED_INTO = 'confetti'

COLORS = (demo.ACCENT, demo.TEAL, '#f2c14e', '#8e7cf0', demo.INK)


def pieces(count=160, seed=0, speed=2200, spread=1.1, angle=-math.pi / 2, colors=COLORS, size=16):
    """The burst's pieces, each a dict of launch velocity `vx, vy` (px/s),
    `w, h`, `color`, `shape` ('strip', 'square' or 'dot'), `spin` and `flip`
    (rad/s), `phase` and `drift` for its sideways flutter, and `drag`. They
    leave in a cone of half-width `spread` (radians) about `angle` (straight
    up by default), at up to `speed`. The same `seed` gives the same burst."""
    rnd = random.Random(f'confetti:{seed}')
    out = []
    for _ in range(count):
        a = angle + rnd.uniform(-spread, spread)
        v = speed * rnd.uniform(0.4, 1.0)
        shape = rnd.choices(('strip', 'square', 'dot'), (5, 3, 2))[0]
        s = size * rnd.uniform(0.7, 1.3)
        out.append(dict(vx=v * math.cos(a), vy=v * math.sin(a), shape=shape, color=rnd.choice(colors),
                        w=s * (0.6 if shape == 'strip' else 1.0), h=s * (1.7 if shape == 'strip' else 1.0),
                        spin=rnd.uniform(-9, 9), flip=rnd.uniform(5, 14), phase=rnd.uniform(0, 2 * math.pi),
                        drift=rnd.uniform(30, 90), drag=rnd.uniform(2.8, 3.8)))
    return out


def place(piece, cx, cy, t, gravity=900):
    """Where `piece` is `t` seconds after leaving (cx, cy): `(x, y, rot, face)`.
    Air drag slows the launch and caps the fall speed, so the pieces hang and
    flutter instead of dropping like stones; `face` (-1 -> 1) is how much of
    the piece is turned to the viewer as it flips end over end."""
    k = piece['drag']
    gone = (1 - math.exp(-k * t)) / k
    x = cx + piece['vx'] * gone + piece['drift'] * math.sin(3 * t + piece['phase']) * min(1, t)
    y = cy + piece['vy'] * gone + gravity / k * (t - gone)
    return x, y, piece['spin'] * t + piece['phase'], math.cos(piece['flip'] * t + piece['phase'])


def draw_confetti(cv, cx, cy, t, burst=None, gravity=900, fade=(2.2, 3.0), **kw):
    """Draw a confetti burst from (cx, cy), `t` seconds after it went off
    (nothing before 0). `burst` is a `pieces()` list (made from `kw` if not
    given; make it once and reuse it for speed). Each piece tumbles and
    flips; the whole burst fades out between the two times in `fade`
    (None to keep it). Call once per frame with the film's time."""
    if t <= 0:
        return
    burst = burst if burst is not None else pieces(**kw)
    alpha = 1.0 if fade is None else 1 - min(1, max(0, (t - fade[0]) / (fade[1] - fade[0])))
    if alpha <= 0:
        return
    c = cv.ctx
    for piece in burst:
        x, y, rot, face = place(piece, cx, cy, t, gravity)
        shade = alpha * (0.55 + 0.45 * abs(face))   # the edge-on side catches less light
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        if piece['shape'] == 'dot':
            c.scale(1, max(0.15, abs(face)))
            demo.dot(cv, 0, 0, piece['w'] / 2, piece['color'], alpha=shade)
        else:
            w, h = piece['w'] * max(0.12, abs(face)), piece['h']
            cv.rect(-w / 2, -h / 2, w, h, piece['color'], radius=min(w, h) * 0.15, alpha=shade)
        c.restore()


BURST = pieces(count=170, seed=3)


def draw(n, cv):
    t = n / demo.FPS - 0.35
    cx, cy = demo.W / 2, demo.H * 0.82
    if -0.35 < t < 0.12:     # a small charge that pops just as the pieces leave
        r = 26 * (1 + 4 * max(0, t))
        demo.dot(cv, cx, cy, r, demo.INK, alpha=1 - max(0, t) / 0.12)
    draw_confetti(cv, cx, cy, t, BURST, fade=(2.4, 2.65))
    cv.mark('burst', cx - 40, cy - 40, 80, 80)

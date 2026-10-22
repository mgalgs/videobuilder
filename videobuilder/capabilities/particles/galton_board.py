"""Galton board: a stream of balls drops through a triangle of pegs, knocked
left or right at every row, and piles up in bins below into a bell curve."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def galton_drops(balls, rows, seed=0):
    """The fate of each of `balls` balls on a board of `rows` peg rows, the
    same every call for one `seed`: a list of `(steps, bin, slot)`, where
    `steps` holds the ball's offset (in peg spacings, centre 0) as it rests on
    each row, `bin` (0..rows) is where it lands and `slot` is how many balls
    reached that bin before it."""
    rng = random.Random(seed)
    filled = [0] * (rows + 1)
    out = []
    for _ in range(balls):
        s, steps = 0.0, []
        for _ in range(rows):
            steps.append(s)
            s += 0.5 if rng.random() < 0.5 else -0.5
        b = round(s + rows / 2)
        out.append((steps, b, filled[b]))
        filled[b] += 1
    return out


def galton_board(cv, t, x, y, w, h, balls=240, rows=10, seed=0, release=1.6, hop=0.06, fall=0.3,
                 color=demo.ACCENT, peg_color=demo.MUTED, wall_color=demo.LINE):
    """Draw a Galton board filling the box (x, y, w, h) at `t` seconds: a
    funnel at the top, `rows` rows of pegs, `rows + 1` bins along the floor.
    `balls` balls leave the funnel evenly over the first `release` seconds,
    take `hop` seconds per peg row and `fall` seconds to drop onto their
    pile, so the last one settles at `release + (rows + 1) * hop + fall`."""
    cx = x + w / 2
    dx = w / (rows + 1)
    r = dx / 9                                   # four balls side by side fill a bin
    cols = 4
    pr = r * 0.8
    mouth = y + h * 0.06
    py = [y + h * 0.14 + k * (h * 0.44 / max(rows - 1, 1)) for k in range(rows)]
    bin_top, ground = y + h * 0.62, y + h

    # the board: funnel, pegs, bin walls, floor
    cv.line(cx - dx * 0.9, y, cx - r * 1.4, mouth, wall_color, width=2)
    cv.line(cx + dx * 0.9, y, cx + r * 1.4, mouth, wall_color, width=2)
    for k, yk in enumerate(py):
        for i in range(k + 1):
            demo.dot(cv, cx + (i - k / 2) * dx, yk, pr, color=peg_color)
    for j in range(rows + 2):
        bx = cx + (j - (rows + 1) / 2) * dx
        cv.line(bx, bin_top, bx, ground, wall_color, width=2)
    cv.line(x, ground, x + w, ground, peg_color, width=3)

    gap = release / max(balls - 1, 1)
    queued = 0
    for i, (steps, b, slot) in enumerate(galton_drops(balls, rows, seed)):
        age = t - i * gap
        if age < 0:                              # still waiting in the funnel: show the next few
            if queued < 5:
                demo.dot(cv, cx, mouth - r - queued * 2.1 * r, r, color=color)
                queued += 1
            continue
        pts = [(cx, mouth)] + [(cx + s * dx, yk - pr - r) for s, yk in zip(steps, py)]
        seg = age / hop
        if seg < len(pts) - 1:                   # hopping peg to peg, a small bounce on each
            k, u = int(seg), seg - int(seg)
            (xa, ya), (xb, yb) = pts[k], pts[k + 1]
            bx = xa + (xb - xa) * u
            by = ya + (yb - ya) * u * u - (yb - ya) * 0.6 * math.sin(math.pi * u) * (k > 0)
        else:                                    # off the last row, down onto its pile
            xa, ya = pts[-1]
            col, level = slot % cols, slot // cols
            xb = cx + (b - rows / 2) * dx + (col - (cols - 1) / 2) * 2.1 * r
            yb = ground - r - 2 - level * 2 * r
            u = vb.clamp01((age - (len(pts) - 1) * hop) / fall)
            bx = xa + (xb - xa) * (1 - (1 - u) ** 2)
            by = ya + (yb - ya) * u * u
        demo.dot(cv, bx, by, r, color=color)
    cv.mark('board', x, y, w, h)


def draw(n, cv):
    galton_board(cv, n / demo.FPS - 0.15, demo.W / 2 - 200, 24, 400, 486, seed=17)


CAPABILITY = Capability(
    id='galton-board',
    name='Galton board',
    family='particles',
    group='Rigid bodies',
    aliases=('bean machine', 'pachinko board', 'quincunx'),
    definition='Many small balls pour through rows of pegs, each nudged left or right at random, '
               'and stack up in bins so the piles trace a bell curve.',
    phrasings=('balls falling through pegs into a bell curve',
               'show a normal distribution building up from dropped beads',
               'plinko-style drop where the counts pile into slots'),
    related=('split-flap-display', 'sierpinski-gasket', 'circle-packing', 'bounce-ease-in',
             'bouncing-ball-word-marker', 'ball-bounce'),
    api=('videobuilder.capabilities.particles.galton_board.galton_board',
         'videobuilder.capabilities.particles.galton_board.galton_drops'),
    demo=lambda: demo.film(draw),
)

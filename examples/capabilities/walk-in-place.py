"""Capability: walk in place. The fox walks while the camera follows: it
stays in the middle and bobs on every step (down with a little squash on
each contact, up on the passing position, leaning forward), while the
ground and the hills scroll past underneath at a steady speed. There are no
leg drawings: this is the bounce-walk of cut-out TV animation, made from one
picture (`Puppet.walk`), not a leg cycle.

    python -m videobuilder preview examples/capabilities/walk-in-place.py

Two steps a beat at 120 bpm, every contact on the beat grid.

LOOP = True: 16 whole steps, and the scroll's travel is a whole number of
tiles of every layer, so the last frame leads into the first.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import parallax, paths, text  # noqa: E402

LOOP = True
GRID = _kit.grid()
FPS = GRID.fps
STEP = GRID.frames_per_beat / 2   # 7.5 frames: two steps a beat
TOTAL = 8 * round(GRID.frames_per_beat)   # 4.0 s, 16 steps
STRIDE = 90                        # px the ground passes each step
TRAVEL = STRIDE * TOTAL / STEP     # 1440: a whole number of tiles in every layer below

GROUND_Y = 560
HILLS, TREES, GROUND, GRASS = '#3a4458', '#24403f', '#1c2622', '#2f4a3c'
FOX = vb.Puppet({'idle': _kit.ASSETS / 'fox' / 'idle.png', 'blink': _kit.ASSETS / 'fox' / 'blink.png'}, height=300)
BLINKS = {44, 45}

TITLE_F = _kit.font(32, 700)


def _hills():
    ridge = parallax.ridge(360, 70, seed=5, bumps=(1, 2))
    shape = [(-1, ridge[0][1])] + ridge + [(361, ridge[-1][1]), (361, 260), (-1, 260)]

    def draw(cv, x):
        paths.draw(cv, [(x + px, GROUND_Y - 170 + py) for px, py in shape], HILLS, fill=True)
    return parallax.Layer(0.25, 360, draw)       # 360 px of travel: one tile


def _trees():
    rnd = random.Random(3)
    trees = [(tx + rnd.uniform(-15, 15), rnd.uniform(90, 130)) for tx in (40, 150, 280)]

    def draw(cv, x):
        for tx, th in trees:
            cx = x + tx
            cv.rect(cx - 4, GROUND_Y - th * 0.35, 8, th * 0.35, TREES)
            paths.draw(cv, [(cx, GROUND_Y - th), (cx + th * 0.24, GROUND_Y - th * 0.28),
                            (cx - th * 0.24, GROUND_Y - th * 0.28)], TREES, fill=True)
    return parallax.Layer(0.5, 360, draw)        # 720 px: two tiles


def _ground():
    def draw(cv, x):
        cv.rect(x - 1, GROUND_Y, 242, 720 - GROUND_Y, GROUND)
        cv.rect(x - 1, GROUND_Y, 242, 6, GRASS)
        for sx, sy, sw in ((20, 26, 70), (150, 26, 40), (90, 62, 56)):
            cv.rect(x + sx, GROUND_Y + sy, sw, 8, GRASS, radius=4)
    return parallax.Layer(1.0, 240, draw)        # 1440 px: six tiles


LAYERS = (_hills(), _trees(), _ground())


def dust(cv, n, x):
    """Two little puffs kicked back off the heel on each contact, gone in four frames."""
    age = (n % STEP)
    if age >= 4:
        return
    a = 1 - age / 4
    for dy, length in ((-6, 22), (-18, 14)):
        x0 = x - 70 - age * 6
        cv.line(x0, GROUND_Y + dy, x0 - length, GROUND_Y + dy, _kit.MUTED, width=3, alpha=0.8 * a)


def draw(n, cv):
    cv.fill(_kit.BG)
    parallax.draw(cv, LAYERS, n * STRIDE / STEP)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Walk in place', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    _kit.label(cv, 'caption', 'Two steps a beat; the ground does the walking', s.x, GROUND_Y + 100, color=_kit.INK)

    g = FOX.walk(n, STEP, rise=0.05, squash=0.06, lean=0.05)
    k = 1 - 0.3 * g.lift / (0.05 * FOX.height)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(s.cx, GROUND_Y + 3)
    ctx.scale(105 * k, 10 * k)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.45 * k)
    ctx.fill()
    ctx.restore()
    dust(cv, n, s.cx)
    # Mirrored, so it faces the way it walks and its tail trails behind.
    FOX.draw(cv, 'blink' if n in BLINKS else 'idle', s.cx, GROUND_Y - g.lift, sx=-g.sx, sy=g.sy, lean=g.lean,
             mark='fox')


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((15, 'contact'), (19, 'passing'), (60, 'contact'), (94, 'passing')))

if __name__ == '__main__':
    vb.main(__file__)

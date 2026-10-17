"""Capability: parallax scene. Five flat layers drawn in code -- a far sky,
hills, a row of trees, the near ground the fox stands on, and grass and a
signpost in the foreground -- slide at their own speeds as the camera pans, so a flat
picture has depth. Each layer is one tile repeated with no seam
(`vb.parallax`).

    python -m videobuilder preview examples/capabilities/parallax-scene.py

It is laid out three ways, each from its format's own table: the catalog's
square, 9:16 and 16:9.

LOOP = True: the camera pans out and back once, and the fox breathes two
whole periods, so the last frame leads into the first.
"""
import math
import random
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, parallax, paths, per_format, text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 120          # 4.0 s
BREATH = 60

F9 = vb.Format('9x16', 720, 1280)
F16 = vb.Format('16x9', 1280, 720)

# The scene's own colours: hazier and lighter far away, darker up close.
SKY_TOP, SKY_LOW = '#101219', '#2a2433'
HILLS, TREES, GROUND, GRASS, NEAR = '#3a4458', '#24403f', '#1c2622', '#2f4a3c', '#08090c'

TITLE_F = _kit.font(32, 700)
FOX = vb.Puppet({'idle': _kit.ASSETS / 'fox' / 'idle.png', 'blink': _kit.ASSETS / 'fox' / 'blink.png'}, height=300)
BLINKS = {52, 53}


def _layout(fmt):
    """Each format's own scene: where the ground meets the hills, how tall
    the hills and trees stand, how far the camera pans, how big the fox is."""
    w, h = fmt.width, fmt.height
    safe = Box(0, 0, w, h).pad(64 if fmt.square else 56)
    if fmt.portrait:      # a tall sky: the ground comes up to give the fox room
        return dict(safe=safe, ground=h * 0.70, hills=300, trees=190, pan=300, fox=1.25)
    if fmt.landscape:     # a wide, low view: a longer pan
        return dict(safe=safe, ground=h * 0.77, hills=170, trees=150, pan=420, fox=0.95)
    return dict(safe=safe, ground=h * 0.74, hills=190, trees=150, pan=320, fox=1.0)


LAYOUTS = {f.name: _layout(f) for f in (_kit.FORMAT, F9, F16)}


# ---- the layers: one tile each, baked at import where they're shapes ----

def _sky(L):
    rnd = random.Random(4)
    stars = [(rnd.uniform(0, 1400), rnd.uniform(0.04, 0.55), rnd.uniform(1.2, 2.6)) for _ in range(40)]

    def draw(cv, x):
        for sx, sy, r in stars:
            cv.ctx.new_path()
            cv.ctx.arc(x + sx, L['ground'] * sy, r, 0, 2 * math.pi)
            cv.ctx.set_source_rgba(0.95, 0.95, 0.93, 0.55)
            cv.ctx.fill()
    return parallax.Layer(0.04, 1400, draw)


def _hills(L):
    top = L['ground'] - L['hills'] - 40
    ridge = parallax.ridge(720, L['hills'] * 0.6, seed=2)
    shape = [(-1, ridge[0][1])] + ridge + [(721, ridge[-1][1]), (721, L['hills'] + 60), (-1, L['hills'] + 60)]

    def draw(cv, x):
        paths.draw(cv, [(x + px, top + py) for px, py in shape], HILLS, fill=True)
    return parallax.Layer(0.2, 720, draw)


def _trees(L):
    base = L['ground'] + 4
    rnd = random.Random(7)
    trees = [(x + rnd.uniform(-20, 20), L['trees'] * rnd.uniform(0.7, 1.0)) for x in (50, 170, 260)]

    def draw(cv, x):
        for tx, th in trees:
            cx = x + tx
            cv.rect(cx - 5, base - th * 0.35, 10, th * 0.35, TREES)
            paths.draw(cv, [(cx, base - th), (cx + th * 0.24, base - th * 0.28), (cx - th * 0.24, base - th * 0.28)],
                       TREES, fill=True)
    return parallax.Layer(0.5, 360, draw)


def _ground(L, h):
    g = L['ground']

    def draw(cv, x):
        cv.rect(x - 1, g, 242, h - g, GROUND)
        cv.rect(x - 1, g, 242, 6, GRASS)
        for sx, sy, sw in ((30, 40, 46), (150, 90, 30), (100, 160, 60)):
            cv.rect(x + sx, g + sy, sw, 8, GRASS, radius=4)
    return parallax.Layer(1.0, 240, draw)


def _near(L, h):
    """Grass and a signpost, near-black, low across the bottom: they sweep across in front of the fox."""
    rnd = random.Random(11)
    blades = [(30 + i * 9 + rnd.uniform(-3, 3), rnd.uniform(80, 200), rnd.uniform(-0.35, 0.35)) for i in range(18)]

    def draw(cv, x):
        for bx, bh, tilt in blades:
            paths.draw(cv, [(x + bx - 7, h + 2), (x + bx + 7, h + 2), (x + bx + tilt * bh, h - bh)], NEAR, fill=True)
        cv.rect(x + 260, L['ground'] - 140, 26, h, NEAR, radius=4)
        cv.rect(x + 230, L['ground'] - 110, 86, 12, NEAR, radius=4)   # a signpost's arm
    return parallax.Layer(1.7, 900, draw)


def _layers(fmt):
    L = LAYOUTS[fmt.name]
    return (_sky(L), _hills(L), _trees(L), _ground(L, fmt.height), _near(L, fmt.height))


LAYERS = {f.name: _layers(f) for f in (_kit.FORMAT, F9, F16)}


def camera(n, L):
    """Pans out and back once: smooth at both ends, so the loop has no seam."""
    return L['pan'] * (1 - math.cos(2 * math.pi * n / TOTAL)) / 2


def draw(n, cv):
    L = per_format(LAYOUTS, cv)
    s = L['safe']
    sky = cairo.LinearGradient(0, 0, 0, L['ground'])
    sky.add_color_stop_rgb(0, *vb.rgba(SKY_TOP)[:3])
    sky.add_color_stop_rgb(1, *vb.rgba(SKY_LOW)[:3])
    cv.ctx.rectangle(0, 0, cv.width, cv.height)
    cv.ctx.set_source(sky)
    cv.ctx.fill()
    cv.ctx.new_path()
    cv.ctx.arc(cv.width * 0.74, L['ground'] - L['hills'] - 150, 46, 0, 2 * math.pi)   # the sun, pinned to the sky
    cv.ctx.set_source_rgba(*vb.rgba(_kit.ACCENT)[:3], 0.9)
    cv.ctx.fill()

    cam = camera(n, L)
    layers = LAYERS[cv.format.name]
    parallax.draw(cv, layers[:4], cam)

    x = cv.width / 2 + L['pan'] / 2 - cam      # the fox stands on the near ground, so it moves with it
    sx, sy = FOX.breath(n, BREATH)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, L['ground'] + 3)
    ctx.scale(110 * L['fox'], 10 * L['fox'])
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    ctx.restore()
    FOX.draw(cv, 'blink' if n in BLINKS else 'idle', x, L['ground'], sx=sx, sy=sy, scale=L['fox'], mark='fox')

    parallax.draw(cv, layers[4:], cam)
    _kit.text_marked(cv, 'title', text.wrap('Parallax scene', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT, F9, F16), background=_kit.BG,
               keyframes=((0, 'start'), (30, 'panning'), (60, 'far end'), (90, 'coming back')))

if __name__ == '__main__':
    vb.main(__file__)

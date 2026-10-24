"""Parallax layers: the same idea as Parallax scene (`parallax_scene.py`),
which keeps the capability -- both are flat `parallax.Layer` tiles drawn
with `parallax.draw`, far ones slow and near ones fast. This module's own
code stays (a film may still import it), but it is no longer a capability
of its own."""
import math

import videobuilder as vb
from videobuilder import parallax, paths

from .. import _demo as demo

MERGED_INTO = 'parallax-scene'

PAN = 900                  # px the ground travels over the demo
HORIZON = demo.H * 0.36
# far to near: hazier and lighter far away, darker up close
BANDS = ((0.15, 1280, '#5b6585', 0, 150, 3), (0.35, 960, '#434c6a', 80, 140, 5),
         (0.6, 800, '#2f3650', 160, 110, 8), (1.0, 640, '#1f2438', 250, 80, 12))


def _band(depth, width, color, top, height, seed):
    ridge = parallax.ridge(width, height, seed=seed)
    shape = [(-1, ridge[0][1])] + ridge + [(width + 1, ridge[-1][1]), (width + 1, demo.H), (-1, demo.H)]
    y0 = HORIZON + top

    def draw(cv, x):
        paths.draw(cv, [(x + px, y0 + py) for px, py in shape], color, fill=True)
    return parallax.Layer(depth, width, draw)


def _trees(depth, width, color, base, heights):
    def draw(cv, x):
        for tx, th in heights:
            cx = x + tx
            cv.rect(cx - 7, base - th * 0.3, 14, th * 0.3 + 4, color)
            for k in range(3):  # three stacked tiers
                y = base - th * (0.25 + 0.25 * k)
                half = th * (0.26 - 0.06 * k)
                paths.draw(cv, [(cx - half, y), (cx + half, y), (cx, y - th * 0.38)], color, fill=True)
    return parallax.Layer(depth, width, draw)


def _grass(depth, width, color):
    blades = [(20 + i * 22, 60 + 50 * (0.5 + 0.5 * math.sin(i * 1.7)), 0.3 * math.sin(i * 2.3)) for i in range(15)]

    def draw(cv, x):
        for bx, bh, tilt in blades:
            paths.draw(cv, [(x + bx - 8, demo.H + 2), (x + bx + 8, demo.H + 2), (x + bx + tilt * bh, demo.H - bh)],
                       color, fill=True)
        cv.rect(x + 470, demo.H - 300, 30, 302, color, radius=6)  # a post sweeping past up close
    return parallax.Layer(depth, width, draw)


LAYERS = (_band(*BANDS[0]), _band(*BANDS[1]),
          _trees(0.5, 520, '#272d44', HORIZON + 210, ((60, 190), (300, 150), (420, 210))),
          _band(*BANDS[2]), _band(*BANDS[3]),
          _grass(1.8, 1100, '#0b0c12'))


def draw(n, cv):
    cv.fill(demo.BG)
    demo.dot(cv, demo.W * 0.72, HORIZON - 150, r=48, color='#f2b632')  # the moon: pinned to the sky
    cam = PAN * vb.ease_in_out_quart(demo.phase(n, 0.2, 2.8))
    parallax.draw(cv, LAYERS, cam)

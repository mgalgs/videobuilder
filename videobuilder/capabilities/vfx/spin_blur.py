"""Spin blur: a picture smeared along circles around a centre point, as if it
were turning too fast for the shutter, so edges near the centre stay crisp
and the rim streaks into rings."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def spin_blur(cv, draw, angle=0.0, amount=0.5, samples=None, cx=None, cy=None):
    """Draw `draw(cv)` turned by `angle` radians (clockwise) about (cx, cy)
    (default the frame's centre), smeared over the `amount` radians it turned
    through just before: copies at every angle from `angle - amount` to
    `angle`, averaged evenly. A negative `amount` trails the other way, for
    anticlockwise spin; 0 draws it sharp. `samples` defaults to about one
    copy per degree of smear. Only what `draw` puts inside the frame turns:
    anything it draws past the edges is cut off before the smear.

    For something spinning at `w` radians a second in a film at `fps`, pass
    `amount=w / fps` (a full-frame shutter; halve it for a 180-degree one)."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    if samples is None:
        samples = math.ceil(abs(math.degrees(amount)))
    n = max(1, int(samples)) if amount else 1
    c = cv.ctx
    c.push_group()
    draw(cv)
    pattern = c.pop_group()
    pattern.set_matrix(cairo.Matrix())  # pattern space = device space, as the group was drawn
    dx, dy = cx * cv.scale, cy * cv.scale  # the copies turn in device space, where the group lives
    c.push_group()
    c.set_operator(cairo.OPERATOR_ADD)  # an exact average: each copy adds 1/n of itself
    for i in range(n):
        a = angle - amount * (1 - (i / (n - 1) if n > 1 else 1))
        c.save()
        c.identity_matrix()
        c.translate(dx, dy)
        c.rotate(a)
        c.translate(-dx, -dy)
        c.set_source(pattern)
        c.paint_with_alpha(1 / n)
        c.restore()
    c.set_operator(cairo.OPERATOR_OVER)
    c.pop_group_to_source()
    c.paint()


# ---- demo: a wheel spins up into a ring of smear, then slows back to sharp ----

TOP = 3.2 * 2 * math.pi  # top speed, radians a second
R = 210


def _ease(x):
    return (1 - math.cos(math.pi * x)) / 2


def _speed(t):
    up = _ease(demo.phase(t * demo.FPS, 0.3, 1.2))
    down = _ease(demo.phase(t * demo.FPS, 1.8, 2.8))
    return TOP * up * (1 - down)


def _turned(n, steps=8):
    """Angle the wheel has turned by frame `n`: its speed summed over time."""
    dt = 1 / (demo.FPS * steps)
    return sum(_speed(k * dt) for k in range(n * steps)) * dt


def _wheel(cv):
    cx, cy = demo.W / 2, demo.H / 2
    for k in range(8):
        a0 = k * math.pi / 4
        cv.sector(cx, cy, R, a0, a0 + math.pi / 4, demo.ACCENT if k % 2 else demo.TEAL)
    for k in range(4):
        a = k * math.pi / 4
        cv.line(cx - R * math.cos(a), cy - R * math.sin(a), cx + R * math.cos(a), cy + R * math.sin(a),
                demo.INK, width=6)
    cv.arc(cx, cy, R, 0, 2 * math.pi, demo.INK, width=9)
    demo.dot(cv, cx + R * 0.72, cy, 18, demo.INK)
    demo.dot(cv, cx, cy, 34, demo.INK)
    demo.dot(cv, cx, cy, 13, demo.BG)


def _draw(n, cv):
    spin_blur(cv, _wheel, _turned(n), _speed(n / demo.FPS) / demo.FPS)


CAPABILITY = Capability(
    id='spin-blur',
    name='Spin blur',
    family='vfx',
    group='Blur & focus',
    aliases=('radial spin blur', 'rotational blur', 'rotary blur', 'circular motion blur'),
    definition='The picture is smeared along circles around a centre point, so it looks like it is '
               'whirling too fast to see, with crisp detail at the hub and streaky rings toward the edge.',
    phrasings=('make the wheel look like it is spinning really fast',
               'blur it round in a circle like it is turning',
               'add a rotating motion blur around the middle'),
    related=('zoom-blur', 'spin', 'blur-dissolve', 'blur-up-image-load', 'refraction-ripple', 'smear-frame'),
    api=('videobuilder.capabilities.vfx.spin_blur.spin_blur',),
    demo=lambda: demo.film(_draw),
)

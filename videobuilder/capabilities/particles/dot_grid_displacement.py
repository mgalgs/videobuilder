"""Dot grid displacement: an evenly spaced field of dots that parts around a
pointer, each dot pushed straight away from it by an amount that fades with
distance, so a round hollow follows the pointer and the grid closes back up
behind it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def displace(px, py, fx, fy, radius=180.0, strength=60.0):
    """How far a point at (px, py) is pushed by a force at (fx, fy): returns
    (dx, dy, k), the offset straight away from the force and its weight
    0 -> 1. The weight falls smoothly from 1 at the force to 0 at `radius`;
    the push is `strength * k` px. A negative `strength` pulls toward it."""
    ox, oy = px - fx, py - fy
    d = math.hypot(ox, oy)
    if d >= radius:
        return 0.0, 0.0, 0.0
    u = 1 - d / radius
    k = u * u * (3 - 2 * u)
    if d < 1e-6:
        return 0.0, 0.0, k
    push = strength * k
    return ox / d * push, oy / d * push, k


def draw_dot_grid(cv, x, y, w, h, pitch, forces, color, hot=None, r=4.0, grow=1.0,
                  radius=180.0, strength=60.0, alpha=1.0):
    """Fill the box (x, y, w, h) with a grid of dots `pitch` px apart, centred
    in the box, each moved by `displace` from every force in `forces` (a list
    of (x, y); offsets add up). A dot of radius `r` grows by up to `grow`
    times its size as it is pushed, and tints toward `hot` if given.
    Returns the box."""
    cols, rows = max(1, int(w // pitch) + 1), max(1, int(h // pitch) + 1)
    x0 = x + (w - (cols - 1) * pitch) / 2
    y0 = y + (h - (rows - 1) * pitch) / 2
    c = cv.ctx
    rest = []
    for j in range(rows):
        for i in range(cols):
            gx, gy = x0 + i * pitch, y0 + j * pitch
            dx = dy = k = 0.0
            for fx, fy in forces:
                ox, oy, kk = displace(gx, gy, fx, fy, radius, strength)
                dx, dy, k = dx + ox, dy + oy, max(k, kk)
            if k <= 0 or hot is None:
                rest.append((gx + dx, gy + dy, r * (1 + grow * k)))
            else:
                cv.sector(gx + dx, gy + dy, r * (1 + grow * k), 0, 2 * math.pi,
                          kit.mix(color, hot, k), alpha=alpha)
    # The undisturbed dots share one colour, so they are filled as one path.
    c.new_path()
    for cx, cy, rr in rest:
        c.new_sub_path()
        c.arc(cx, cy, rr, 0, 2 * math.pi)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    # The pointer glides in from the left, loops through the grid, and leaves on the right so it settles.
    p = demo.phase(n, 0.15, 2.85)
    cx = -120 + (demo.W + 240) * (0.5 - 0.5 * math.cos(math.pi * p))
    cy = demo.H / 2 + 200 * math.sin(2 * math.pi * p * 1.5) * math.sin(math.pi * p)
    box = draw_dot_grid(cv, 60, 60, demo.W - 120, demo.H - 120, 40, [(cx, cy)], demo.MUTED,
                        hot=demo.ACCENT, r=5, grow=1.2, radius=230, strength=70)
    cv.mark('grid', *box)
    # The pointer itself: a ring with a small centre dot.
    pulse = 1 + 0.06 * math.sin(2 * math.pi * t * 2)
    cv.sector(cx, cy, 6, 0, 2 * math.pi, demo.INK)
    c = cv.ctx
    c.new_path()
    c.arc(cx, cy, 26 * pulse, 0, 2 * math.pi)
    c.set_source_rgba(*vb.rgba(demo.INK, 0.9))
    c.set_line_width(3)
    c.stroke()


CAPABILITY = Capability(
    id='dot-grid-displacement',
    name='Dot grid displacement',
    family='particles',
    group='Interaction fields',
    aliases=('dot grid repel', 'interactive dot field', 'magnetic dot grid', 'cursor repel grid'),
    definition='A pointer moving over a regular grid of dots shoves the nearby dots outward, '
               'less the farther away they sit, and the grid eases back into rows once it passes.',
    phrasings=('a field of dots that moves out of the way of the cursor',
               'grid of dots that gets pushed apart wherever the mouse goes',
               'dots ripple away from a point moving across a dotted background'),
    related=('cursor-follower-dot-and-ring', 'bouncing-dots', 'dot-matrix-text', 'halftone-dot-scaling',
             'dot-density-map', 'hover-letter-displacement'),
    api=('videobuilder.capabilities.particles.dot_grid_displacement.draw_dot_grid',
         'videobuilder.capabilities.particles.dot_grid_displacement.displace'),
    demo=lambda: demo.film(draw),
)

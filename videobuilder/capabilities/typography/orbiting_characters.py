"""Orbiting characters: the letters of a word each circle a common centre on
their own tilted ellipse, inner rings turning faster than outer ones."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def orbits(text, t, cx, cy, r0=90, gap=55, squash=0.6, tilt=-0.35, speed=0.5, seed=0):
    """Where each character of `text` is at time `t` (seconds) as `(char, x, y)`,
    one ring per character from radius `r0` out in steps of `gap`. Rings are
    ellipses flattened by `squash` and turned by `tilt` radians about (cx, cy).
    The innermost ring makes `speed` turns a second and each ring outward
    slows like a planet's (period grows as radius^1.5). Starting angles are
    spread by a golden-angle step offset by `seed`. Spaces are skipped."""
    out = []
    chars = [ch for ch in text if not ch.isspace()]
    ct, st = math.cos(tilt), math.sin(tilt)
    for i, ch in enumerate(chars):
        r = r0 + gap * i
        rate = speed * (r0 / r) ** 1.5
        a = seed + i * 2.39996 + 2 * math.pi * rate * t
        ex, ey = r * math.cos(a), r * squash * math.sin(a)
        out.append((ch, cx + ex * ct - ey * st, cy + ex * st + ey * ct))
    return out


def ring(cx, cy, r, squash=0.6, tilt=-0.35, steps=96):
    """The points of one orbit (as `orbits` lays them out), for drawing the track."""
    ct, st = math.cos(tilt), math.sin(tilt)
    pts = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        ex, ey = r * math.cos(a), r * squash * math.sin(a)
        pts.append((cx + ex * ct - ey * st, cy + ex * st + ey * ct))
    return pts


def draw_orbiting(cv, text, font, cx, cy, t, color, tracks=None, r0=90, gap=55, squash=0.6, tilt=-0.35,
                  alpha=1.0, **kw):
    """Draw `text` orbiting (cx, cy) at time `t`, each glyph centred on its point.
    `tracks`: a colour to draw the faint orbit rings in first (None: no rings).
    `kw` goes to `orbits` (`speed`, `seed`)."""
    placed = orbits(text, t, cx, cy, r0=r0, gap=gap, squash=squash, tilt=tilt, **kw)
    if tracks is not None:
        for i in range(len(placed)):
            vb.paths.draw(cv, ring(cx, cy, r0 + gap * i, squash, tilt), tracks, width=1.5, closed=True,
                          alpha=0.35 * alpha)
    for ch, x, y in placed:
        w, h = vb.text.block_size([ch], font)
        vb.text.draw(cv, [ch], font, x - w / 2, y - h / 2, color, alpha=alpha)
    return placed


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    t = n / demo.FPS
    fade = demo.phase(n, 0.0, 0.4)
    draw_orbiting(cv, 'ORBIT', demo.font(64, 800), cx, cy, t, demo.INK, tracks=demo.MUTED,
                  r0=100, gap=58, speed=0.45, seed=0.6, alpha=fade)
    demo.dot(cv, cx, cy, r=10, color=demo.ACCENT)
    cv.mark('centre', cx - 10, cy - 10, 20, 20)


CAPABILITY = Capability(
    id='orbiting-characters',
    name='Orbiting characters',
    family='typography',
    group='Path and orbit',
    aliases=('letter orbit', 'planetary text'),
    definition='Each letter of a word circles a shared centre on its own oval track, '
               'the inner ones lapping faster than the outer ones.',
    phrasings=('make the letters spin around a point like planets',
               'each character circles the middle on its own ring',
               'the letters of the title orbit a dot like a tiny solar system'),
    related=('orbit', 'two-body-orbit', 'character-rotate-in', 'orbit-loader', 'orbital-pulse',
             'character-slide-in'),
    api=('videobuilder.capabilities.typography.orbiting_characters.draw_orbiting',
         'videobuilder.capabilities.typography.orbiting_characters.orbits'),
    demo=lambda: demo.film(draw),
)

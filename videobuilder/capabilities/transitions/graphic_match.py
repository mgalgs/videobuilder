"""Graphic Match: the same idea as Match Cut (`match_cut.py`, which keeps the
capability) -- a hard cut between two scenes that share a shape in the same
place and size, so the eye carries the shape over the cut. This module's own
code stays (a film may still import it), but it is no longer a capability of
its own."""
import math

from .. import _demo as demo

MERGED_INTO = 'match-cut'


def graphic_match(cv, a, b, p, at=None, zoom=1.35, cut=0.5):
    """Draw the match at progress `p` (0 -> 1): `a(cv)` pushes in on the point
    `at` (default the frame centre), a hard cut to `b(cv)` at `cut`, and `b`
    pulls back out from the same point. Both scenes are scaled alike about
    `at`, peaking at `zoom` on the cut with no motion there, so a shape that
    sits at `at` in both scenes at the same size lines up exactly.

    The match itself is in the composition: put the shared shape (a circle,
    a bar, a silhouette) at the same place and size in `a` and `b`. In a
    film, call it while both shots are live in an overlap, e.g.
    `graphic_match(cv, lambda c: moon(c), lambda c: clock(c), f / overlap_frames, at=(cx, cy))`."""
    ax, ay = at if at is not None else (cv.width / 2, cv.height / 2)
    s = 1 + (zoom - 1) * math.sin(math.pi * min(max(p, 0.0), 1.0)) ** 2
    with cv.layer(dx=ax * (1 - s), dy=ay * (1 - s), scale=s):
        (a if p < cut else b)(cv)


# ---- demo: a full moon cuts to a clock face of the same size, same place ----
CX, CY, R = demo.W * 0.62, demo.H * 0.44, 120


def moon_scene(cv):
    cv.fill('#0f1830')
    for i, (x, y) in enumerate(((90, 70), (220, 160), (330, 60), (130, 260), (820, 90), (900, 220), (450, 130))):
        demo.dot(cv, x, y, r=2 + i % 2, color=demo.INK, alpha=0.7)
    demo.dot(cv, CX, CY, r=R + 26, color='#f3eed8', alpha=0.08)
    demo.dot(cv, CX, CY, r=R, color='#f3eed8')
    for dx, dy, r in ((-40, -30, 26), (35, 20, 18), (-10, 55, 14), (50, -50, 10)):
        demo.dot(cv, CX + dx, CY + dy, r=r, color='#d9d2b8')
    for hx, hr in ((120, 260), (480, 300), (860, 240)):
        demo.dot(cv, hx, demo.H + hr * 0.55, r=hr, color='#070b16')


def clock_scene(cv):
    cv.fill('#e9e6df')
    cv.rect(0, demo.H * 0.8, demo.W, demo.H * 0.2, '#d6d1c6')
    demo.dot(cv, CX, CY + 6, r=R + 4, color='#000000', alpha=0.18)
    demo.dot(cv, CX, CY, r=R, color=demo.ACCENT)
    demo.dot(cv, CX, CY, r=R - 14, color='#fbfaf6')
    for i in range(12):
        t = i * math.pi / 6
        r0 = R - 32 if i % 3 == 0 else R - 26
        cv.line(CX + r0 * math.sin(t), CY - r0 * math.cos(t), CX + (R - 20) * math.sin(t),
                CY - (R - 20) * math.cos(t), demo.BG, width=5 if i % 3 == 0 else 2)
    for t, length, w in ((math.radians(300), 52, 8), (math.radians(60), 82, 5)):
        cv.line(CX, CY, CX + length * math.sin(t), CY - length * math.cos(t), demo.BG, width=w)
    demo.dot(cv, CX, CY, r=8, color=demo.ACCENT)


def demo_film():
    return demo.two_scenes(lambda cv, a, b, p: graphic_match(cv, a, b, p, at=(CX, CY)),
                           start=0.5, length=2.0, a=moon_scene, b=clock_scene)

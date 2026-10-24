"""Whiteboard marker drawing: the same idea as Drawn-on diagram
(`../shapes/drawn_on_diagram.py`), which keeps the capability -- both draw
a whiteboard diagram stroke by stroke with paths.reveal plus paths.jitter:
a hand holding a marker draws a diagram on a white board, stroke after
stroke, the ink trailing the pen nib as it goes. This module's own code
stays (a film may still import it), but it is no longer a capability of
its own."""
import math

import videobuilder as vb

from ... import paths
from .. import _demo as demo

MERGED_INTO = 'drawn-on-diagram'

BOARD = '#eef0f1'
MARKER_INK = '#1c1d22'
SKIN = '#d9dbe0'


def marker_drawing(cv, strokes, p, color=MARKER_INK, width=3.0, lift=0.25, hand=True, scale=1.0):
    """Draw `strokes` at progress `p` (0 -> 1) as if a marker were drawing
    them one after another, and return the nib's (x, y) (None once done or
    before it starts). Each stroke is a point list or a `(points, color)`
    pair; its share of the time is its arc length plus `lift` of the mean
    stroke length for the pen hop before it, so the nib keeps one speed.
    Finished strokes stay drawn; the current one ends at the nib. `hand`:
    draw the hand and marker at the nib (see `draw_marker`), `scale` sizing it.
    Bake hand wobble into the points once (`paths.jitter`), not per frame."""
    items = [(s, color) if not isinstance(s[1], str) else s for s in strokes]
    lengths = [paths.length(pts) for pts, _ in items]
    hop = lift * (sum(lengths) / len(lengths) if lengths else 0)
    total = sum(lengths) + hop * len(lengths)
    at = vb.clamp01(p) * total
    tip = None
    for (pts, ink), length in zip(items, lengths):
        at -= hop
        if at <= 0:
            break
        part = 1.0 if at >= length - 1e-6 else at / length
        shown = paths.reveal(pts, part)
        paths.draw(cv, shown, ink, width=width)
        if part < 1:
            tip = shown[-1]
            break
        at -= length
    if hand and tip is not None:
        draw_marker(cv, *tip, scale=scale)
    return tip


def draw_marker(cv, x, y, scale=1.0, body=MARKER_INK, band=demo.ACCENT, skin=SKIN, angle=-55):
    """A hand gripping a marker whose nib touches (x, y): the barrel leans
    back up and to the right at `angle` degrees, the hand wrapped round it."""
    a = math.radians(angle)
    ux, uy = math.cos(a) * scale, math.sin(a) * scale          # along the barrel, away from the nib
    vx, vy = -uy, ux                                           # across it

    def pt(u, v):
        return (x + ux * u + vx * v, y + uy * u + vy * v)

    def blob(cu, cv_, ru, rv, k=24):
        return [pt(cu + ru * math.cos(t), cv_ + rv * math.sin(t))
                for t in (2 * math.pi * i / k for i in range(k))]

    palm = blob(70, 24, 36, 30)                                 # the palm sits behind the barrel
    paths.draw(cv, palm, skin, fill=True)
    paths.draw(cv, palm, '#6f7380', width=1.5 * scale, closed=True)
    paths.draw(cv, [pt(0, -1.5), pt(0, 1.5), pt(9, 5), pt(9, -5)], body, fill=True)       # nib
    paths.draw(cv, [pt(8, -8), pt(8, 8), pt(80, 8), pt(80, -8)], body, fill=True)        # barrel
    paths.draw(cv, [pt(20, -8.5), pt(20, 8.5), pt(40, 8.5), pt(40, -8.5)], band, fill=True)  # label band
    for u in (46, 60):                                          # two fingers curled over the barrel
        finger = blob(u, 6, 7, 16, k=16)
        paths.draw(cv, finger, skin, fill=True)
        paths.draw(cv, finger, '#6f7380', width=1.5 * scale, closed=True)


def _circle(cx, cy, r, k=40, start=-math.pi / 2):
    return [(cx + r * math.cos(start + 2 * math.pi * i / k), cy + r * math.sin(start + 2 * math.pi * i / k))
            for i in range(k + 1)]


def _diagram():
    """An idea -> process -> result explainer: three framed panels and two arrows."""
    cy, pw, ph = 262, 150, 170
    xs = (140, 405, 670)
    raw = []
    for i, x0 in enumerate(xs):
        y0 = cy - ph / 2
        raw.append([(x0, y0), (x0 + pw, y0), (x0 + pw, y0 + ph), (x0, y0 + ph), (x0, y0 - 2)])
        mx = x0 + pw / 2
        if i == 0:                                              # a bulb: glass, rays, base
            raw.append(_circle(mx, cy - 12, 26))
            for k in range(5):
                t = math.pi + math.pi * (k + 0.5) / 5
                raw.append([(mx + 36 * math.cos(t), cy - 12 + 36 * math.sin(t)),
                            (mx + 48 * math.cos(t), cy - 12 + 48 * math.sin(t))])
            raw.append(([(mx - 16, cy + 36), (mx + 16, cy + 36)], demo.ACCENT))
        elif i == 1:                                            # a gear: ring, hub, teeth
            raw.append((_circle(mx, cy, 34), demo.ACCENT))
            raw.append(_circle(mx, cy, 12, k=24))
            for k in range(6):
                t = 2 * math.pi * k / 6
                raw.append(([(mx + 34 * math.cos(t), cy + 34 * math.sin(t)),
                             (mx + 48 * math.cos(t), cy + 48 * math.sin(t))], demo.ACCENT))
        else:                                                   # a tick inside a circle
            raw.append(_circle(mx, cy, 40))
            raw.append(([(mx - 20, cy + 2), (mx - 5, cy + 18), (mx + 22, cy - 16)], demo.TEAL))
        if i < 2:                                               # arrow to the next panel
            ax0, ax1 = x0 + pw + 22, xs[i + 1] - 22
            raw.append([(ax0, cy), (ax1, cy)])
            raw.append([(ax1 - 14, cy - 12), (ax1, cy), (ax1 - 14, cy + 12)])
    out = []
    for n, s in enumerate(raw):
        pts, ink = (s, None) if not isinstance(s[1], str) else s
        pts = paths.jitter(paths.resample(pts, max(8, int(paths.length(pts) / 6))), seed=n, amount=1.2)
        out.append((pts, ink) if ink else pts)
    return out


DIAGRAM = _diagram()


def draw(n, cv):
    cv.rect(60, 50, demo.W - 120, demo.H - 100, BOARD, radius=14)
    cv.mark('board', 60, 50, demo.W - 120, demo.H - 100)
    marker_drawing(cv, DIAGRAM, demo.phase(n, 0.15, 2.6), width=3.5, scale=1.3)

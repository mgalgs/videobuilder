"""Blueprint: chalk lines on a scrolling grid. The scene's outlines draw
themselves in one after another (on `age`), then the beacon's beams sweep
as dashed lines, swell lines roll across the water and a compass rose
turns in the corner.

Options: `font` -- a vb.Font for the dimension labels (none without it)."""
import math

from . import kit
from .look import Look
from .. import paths, text
from ..ease import clamp01, ease_in_out_quart

PAPER = '#1a4a8c'
GRIDLINE = '#3a74ba'
CHALK = '#e8f2ff'
DRAW_IN = 1.6     # seconds for the whole scene to draw itself in


def paint(cv, scene, t, age, font=None):
    u = scene.u
    w, h = scene.w, scene.h
    cv.rect(0, 0, w, h, PAPER)
    pitch = 40 * u
    off = (t * 30 * u) % pitch                      # the sheet slides under the drawing
    k = 0
    x = 0.0
    while x < w + pitch:
        cv.line(x - off, 0, x - off, h, GRIDLINE, width=(1.5 if k % 5 else 3) * u)
        x += pitch
        k += 1
    k = 0
    y = 0.0
    while y < h + pitch:
        cv.line(0, y - off, w, y - off, GRIDLINE, width=(1.5 if k % 5 else 3) * u)
        y += pitch
        k += 1
    draw_p = clamp01(age / DRAW_IN)                  # the drawing draws itself in, line by line
    lines = [r.points + [r.points[0]] for r in scene.regions if r.role not in ('sky', 'water')]
    if scene.sun:
        circle = kit.circle_pts(*scene.sun, 96)
        lines.append(circle + [circle[0]])
    if scene.horizon is not None:
        lines.append([(0, scene.horizon), (w, scene.horizon)])
    n = max(1, len(lines))
    for i, pts in enumerate(lines):
        frac = ease_in_out_quart(clamp01(draw_p * (n * 0.7 + 1) - i * 0.7))
        if frac > 0:
            paths.draw(cv, paths.reveal(pts, frac), CHALK, width=4 * u)
    if draw_p >= 1:
        cv.ctx.set_dash([18 * u, 12 * u], -60 * u * t)     # the dashes march outwards
        for pts, s in kit.beams(scene, t):
            paths.draw(cv, [pts[0], pts[1]], CHALK, width=2 * u, alpha=s)
            paths.draw(cv, [pts[3], pts[2]], CHALK, width=2 * u, alpha=s)
        cv.ctx.set_dash([])
    if scene.horizon is not None:
        reveal = clamp01(draw_p * 2 - 1)
        row, y = 0, scene.horizon + 40 * u
        while reveal > 0 and y < h:                   # swell lines, rolling in
            pts = []
            x = row * 6 * u
            while x < w + 16 * u:
                if scene.role_at(x, y) == 'water':
                    pts.append((x, y + 18 * u * math.sin(x / (50 * u) - t * 3.5 + row)))
                elif len(pts) > 1:
                    paths.draw(cv, paths.reveal(pts, reveal), CHALK, width=3 * u, alpha=0.75)
                    pts = []
                else:
                    pts = []
                x += 12 * u
            if len(pts) > 1:
                paths.draw(cv, paths.reveal(pts, reveal), CHALK, width=3 * u, alpha=0.75)
            y += 56 * u
            row += 1
    dim = clamp01((age / DRAW_IN - 0.6) * 2.5)
    tallest = max(scene.of('building') or [None], key=lambda r: r.bbox[3] if r else 0)
    if dim > 0 and tallest:                         # a dimension line up the tallest building
        x0, y0, rw, rh = tallest.bbox
        group = [r.bbox for r in scene.regions if r.role in ('building', 'light')
                 and r.bbox[0] < x0 + rw and r.bbox[0] + r.bbox[2] > x0]
        top = min(b[1] for b in group)
        lx = x0 - 50 * u
        with cv.layer(opacity=dim):
            cv.line(lx, top, lx, y0 + rh, CHALK, width=2 * u)
            for yy in (top, y0 + rh):
                cv.line(lx - 20 * u, yy, lx + 20 * u, yy, CHALK, width=2 * u)
            if font:
                label = (f'H {round((y0 + rh - top) / (13.4 * u))} m',)
                tw, th = text.block_size(label, font)
                text.draw(cv, label, font, lx - 14 * u - tw, (top + y0 + rh) / 2 - th / 2, CHALK)
    cx, cy = w - 110 * u, h - 110 * u                  # a compass rose, turning slowly
    for i in range(8):
        ang = i * math.pi / 4 + t * 0.4
        r = (70 if i % 2 == 0 else 38) * u
        paths.draw(cv, [(cx, cy), (cx + r * math.cos(ang), cy + r * math.sin(ang))], CHALK, width=3 * u)
    cv.arc(cx, cy, 52 * u, 0, 2 * math.pi, CHALK, width=2 * u)


LOOK = Look('blueprint', 'Blueprint', 'the scene draws itself in chalk', paint,
            aliases=('technical drawing', 'schematic', 'chalk', 'drafting', 'architectural'))

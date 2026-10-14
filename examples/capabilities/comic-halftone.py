"""Capability: comic-book halftone. A flat-colour ball with a halftone-dot
shadow half (`videobuilder.canvas.halftone_pattern`), a thick ink outline,
and a jittering starburst callout with a short word -- the dot plate sits a
couple of pixels off from the ink, the way an old four-colour print
misregisters its plates.

    python -m videobuilder preview examples/capabilities/comic-halftone.py

LOOP = True: the one hero move (the starburst's wobble) is a sum of sines at
frequencies that are whole multiples of 1/PERIOD, so it is an exact period --
frame 0 and the frame just past the last are the same point in the cycle by
construction. Nothing else moves.

Its own small palette (STYLE.md's style-card exception): paper cream, ink,
a deep red, a shading blue and a flat yellow -- 5 colours, chosen for the
same contrast and colour-blind rules as the rest of the catalog.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
PERIOD = 96   # 3.2 s true period

PAPER = '#f4ecd8'
INK = '#15120f'
RED = '#c81e3a'
BLUE = '#2e6f9e'
YELLOW = '#f0a202'

TITLE_F = _kit.font(32, 700)
BURST_F = _kit.font(26, 700)

BALL_CX, BALL_CY, BALL_R = 260, 460, 150
MISREG = (3.0, -3.0)   # the dot plate sits this far off from the ink

BURST_CX, BURST_CY = 560, 190
BURST_R_OUT, BURST_R_IN = 86, 44
BURST_SPIKES = 11


def circle_path(ctx, cx, cy, r):
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)


def star_points(cx, cy, r_out, r_in, n):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def draw_ball(cv):
    ctx = cv.ctx
    ctx.save()
    circle_path(ctx, BALL_CX, BALL_CY, BALL_R)
    ctx.clip()
    cv.rect(BALL_CX - BALL_R, BALL_CY - BALL_R, 2 * BALL_R, 2 * BALL_R, YELLOW)
    ctx.save()
    ctx.rectangle(BALL_CX, BALL_CY - BALL_R, BALL_R, 2 * BALL_R)   # the shadow half
    ctx.clip()
    ctx.translate(*MISREG)
    ctx.set_source(vb.halftone_pattern(14, 4.6, angle=0.5, color=BLUE))
    ctx.paint()
    ctx.restore()
    ctx.restore()
    cv.line(BALL_CX, BALL_CY - BALL_R, BALL_CX, BALL_CY + BALL_R, INK, width=4)
    cv.arc(BALL_CX, BALL_CY, BALL_R - 4, 0, 2 * math.pi, INK, width=9)
    cv.mark('ball', BALL_CX - BALL_R, BALL_CY - BALL_R, 2 * BALL_R, 2 * BALL_R)


def wobble(n):
    """A sum of sines at harmonics of 1/PERIOD: an irregular-looking jitter
    that is nonetheless an exact period, so it loops with no seam."""
    p = n / PERIOD
    rot = math.radians(7) * math.sin(2 * math.pi * 3 * p) + math.radians(3) * math.sin(2 * math.pi * 7 * p + 1.3)
    scale = 1.0 + 0.07 * math.sin(2 * math.pi * 5 * p + 0.4)
    return rot, scale


def draw_burst(cv, n):
    rot, scale = wobble(n)
    with cv.layer(dx=BURST_CX - BURST_CX * scale, dy=BURST_CY - BURST_CY * scale, scale=scale):
        ctx = cv.ctx
        ctx.save()
        ctx.translate(BURST_CX, BURST_CY)
        ctx.rotate(rot)
        ctx.translate(-BURST_CX, -BURST_CY)
        pts = star_points(BURST_CX, BURST_CY, BURST_R_OUT, BURST_R_IN, BURST_SPIKES)
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(RED))
        ctx.fill_preserve()
        ctx.set_source_rgba(*vb.rgba(INK))
        ctx.set_line_width(6)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.restore()
        box = text.block_size(['POW'], BURST_F)
        text.draw(cv, ['POW'], BURST_F, BURST_CX - box[0] / 2, BURST_CY - box[1] / 2, PAPER)
    r = BURST_R_OUT * 1.1   # a little slack for the wobble's scale peak
    cv.mark('burst', BURST_CX - r, BURST_CY - r, 2 * r, 2 * r)


def draw(n, cv):
    cv.fill(PAPER)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Comic-book halftone', TITLE_F, s.w), TITLE_F, s.x, s.y, INK)
    draw_ball(cv)
    draw_burst(cv, n)


FILM = vb.Film(draw=draw, fps=FPS, frames=PERIOD, formats=(_kit.FORMAT,), background=PAPER,
               keyframes=(0, PERIOD // 3, 2 * PERIOD // 3))

if __name__ == '__main__':
    vb.main(__file__)

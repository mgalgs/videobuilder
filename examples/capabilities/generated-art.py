"""Capability: generated art. A field of flowing arcs, seeded so the exact
same pattern reproduces every render, drawn with raw cairo paths and a
gradient via `cv.ctx` directly.

    python -m videobuilder preview examples/capabilities/generated-art.py

LOOP = True: the whole field is driven by one continuous wrapping phase
(`n % PERIOD / PERIOD`), so frame 0 and the frame just past the last are the
same point in the cycle by construction -- no enter/exit needed.
"""
import math
import random
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402
from videobuilder.canvas import rgba  # noqa: E402

LOOP = True
PERIOD = 90   # 3.0 s true period at 30 fps
SEED = 7

CAPTION_F = _kit.font(22, 600)

# A fixed field of arcs: seeded once, at import time, so the pattern itself
# (positions, radii, phase offsets) is exactly reproducible across renders.
_rnd = random.Random(SEED)
N = 42
FIELD = [
    dict(
        cx=_rnd.uniform(90, 630),
        cy=_rnd.uniform(140, 560),
        r=_rnd.uniform(26, 92),
        a0=_rnd.uniform(0, 2 * math.pi),
        span=_rnd.uniform(0.9, 2.6),
        speed=_rnd.choice((-1, 1)) * _rnd.uniform(0.6, 1.4),
        width=_rnd.uniform(2.0, 4.5),
        teal=_rnd.random() < 0.38,
    )
    for _ in range(N)
]


def draw(n, cv):
    cv.fill(_kit.BG)
    phase = (n % PERIOD) / PERIOD   # wraps 0..1 .. 0, a true period
    c = cv.ctx

    for i, f in enumerate(FIELD):
        ang = f['a0'] + f['speed'] * 2 * math.pi * phase
        c.save()
        c.set_line_width(f['width'])
        if f['teal']:
            # the teal arcs stroke with a linear gradient along their own
            # chord, teal sweeping into the accent colour -- a gradient on
            # real path geometry, not a wash laid over the whole frame
            x0, y0 = f['cx'] + f['r'] * math.cos(ang), f['cy'] + f['r'] * math.sin(ang)
            x1, y1 = f['cx'] + f['r'] * math.cos(ang + f['span']), f['cy'] + f['r'] * math.sin(ang + f['span'])
            grad = cairo.LinearGradient(x0, y0, x1, y1)
            tr, tg, tb, _ = rgba(_kit.TEAL)
            ar, ag, ab, _ = rgba(_kit.ACCENT)
            grad.add_color_stop_rgba(0.0, tr, tg, tb, 0.55)
            grad.add_color_stop_rgba(1.0, ar, ag, ab, 0.55)
            c.set_source(grad)
        else:
            r, g, b, _ = rgba(_kit.ACCENT)
            c.set_source_rgba(r, g, b, 0.55)
        c.arc(f['cx'], f['cy'], f['r'], ang, ang + f['span'])
        c.stroke()
        c.restore()

    cv.mark('field', 60, 120, 600, 460)
    cap = text.wrap('Generated — seeded, reproducible', CAPTION_F, 400)
    cw, ch = text.block_size(cap, CAPTION_F)
    _kit.text_marked(cv, 'caption', cap, CAPTION_F, cv.width / 2 - cw / 2, cv.height - 76, _kit.MUTED,
                      align='center', width=400)


FILM = vb.Film(draw=draw, fps=30, frames=PERIOD, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(0, PERIOD // 3, 2 * PERIOD // 3))

if __name__ == '__main__':
    vb.main(__file__)

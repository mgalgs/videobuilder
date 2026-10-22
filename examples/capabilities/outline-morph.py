"""Capability: shape morph. A circle turns into a document icon and back --
one idea becoming the next instead of a cut between them -- built on
`videobuilder.paths.morph`: both outlines are resampled to the same point
count and interpolated with a smooth ease, with colour travelling along.

    python -m videobuilder preview examples/capabilities/outline-morph.py

LOOP = True: the clip rests on the settled circle at both ends (frame 0 and
the last few frames are the same quiet "circle, not yet morphing" state), the
same convention as overlap-transitions.py.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import paths, text  # noqa: E402
from videobuilder.canvas import rgba  # noqa: E402

LOOP = True
FPS = 30
HOLD, MORPH = 20, 22   # frames resting on a shape, frames morphing between them
TOTAL = HOLD + MORPH + HOLD + MORPH + HOLD   # rests on the circle at both ends

TITLE_F = _kit.font(32, 700)
CAPTION_F = _kit.font(22, 600)

CX, CY, R = 360, 390, 150


def circle_points(n=56):
    return [(CX + R * math.cos(2 * math.pi * i / n), CY + R * math.sin(2 * math.pi * i / n)) for i in range(n)]


def doc_points():
    """A document icon: a rounded-ish rect with a folded top-right corner,
    as a coarse polygon -- `morph` resamples it to match the circle's point
    count, so the coarse corners don't need to match in number."""
    w, h, fold = 220, 280, 46
    x0, y0 = CX - w / 2, CY - h / 2
    x1, y1 = CX + w / 2, CY + h / 2
    return [(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)]


CIRCLE = circle_points()
DOC = doc_points()


def ease_smootherstep(t):
    """6t^5 - 15t^4 + 10t^3: zero velocity and curvature at both ends, so the
    morph starts and lands softly instead of snapping into motion."""
    return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3


def shape_phase(n):
    """0 (circle) .. 1 (document) .. 0 (circle again), both ends at rest."""
    n = n % TOTAL
    if n < HOLD:
        return 0.0
    n -= HOLD
    if n < MORPH:
        return ease_smootherstep(n / MORPH)
    n -= MORPH
    if n < HOLD:
        return 1.0
    n -= HOLD
    if n < MORPH:
        return 1.0 - ease_smootherstep(n / MORPH)
    return 0.0


def lerp_color(a, b, t):
    """A colour between `a` and `b`, as an (r, g, b) tuple of 0-255 channels
    -- `rgba`'s own input range, since `cv.rect`/`paths.draw` take colours,
    not the 0-1 floats `rgba` returns."""
    ar, ag, ab, _ = rgba(a)
    br, bg, bb, _ = rgba(b)
    return tuple(255 * (x + (y - x) * t) for x, y in ((ar, br), (ag, bg), (ab, bb)))


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Outline morph', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    t = shape_phase(n)
    shape = paths.morph(CIRCLE, DOC, t, closed=True)
    r, g, b = lerp_color(_kit.ACCENT, _kit.TEAL, t)
    paths.draw(cv, shape, (r, g, b), fill=True)
    paths.draw(cv, shape, _kit.INK, width=3, closed=True)
    xs = [p[0] for p in shape]
    ys = [p[1] for p in shape]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    label = 'Circle' if t < 0.5 else 'Document'
    _kit.label(cv, 'caption', label, s.x, s.bottom - 28, align='left')


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((HOLD // 2, 'circle'), (HOLD + MORPH + HOLD // 2, 'document')))

if __name__ == '__main__':
    vb.main(__file__)

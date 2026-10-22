"""Handwriting Reveal: a word appears as if written by an unseen pen, the ink
line growing stroke by stroke at a steady hand's pace, then the pen lifts.

videobuilder has the geometry (`paths.reveal`, `paths.jitter`) but nothing
that writes a set of strokes in order at one pen speed, so that lives here:
`smooth` turns a few control points into a curved stroke, `write_on` draws
any list of strokes written up to progress `p`. The strokes are the writer's
centre lines (a signature, a hand-lettered word, a scribbled label), not a
font's outlines.
"""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def smooth(points, steps=12):
    """A Catmull-Rom curve through `points` (film px), `steps` samples per
    hop: a few hand-placed control points become a flowing pen stroke that
    passes through every one of them."""
    pts = list(points)
    if len(pts) < 3:
        return pts
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append((0.5 * (2 * x1 + (x2 - x0) * t + (2 * x0 - 5 * x1 + 4 * x2 - x3) * t2
                               + (3 * x1 - x0 - 3 * x2 + x3) * t3),
                        0.5 * (2 * y1 + (y2 - y0) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2
                               + (3 * y1 - y0 - 3 * y2 + y3) * t3)))
    out.append(pts[-1])
    return out


def _stroke(cv, pts, color, width, alpha):
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for q in pts[1:]:
        c.line_to(*q)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.set_line_width(width)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke()


def write_on(cv, strokes, p, color, width=6, lift=0.35, nib=None, alpha=1.0):
    """Draw `strokes` (point lists, in writing order) written up to progress
    `p` (0 -> 1): the pen moves at one speed along their total arc length,
    and between strokes it travels with the ink off for `lift` of a stroke's
    average length, so a dotted i or crossed t lands after a beat. Lines are
    `width` px with round ends. `nib`: a colour to mark the pen tip with while
    it writes (None: no tip). Returns the tip's (x, y), or None when the pen is
    up or done."""
    lens = [vb.paths.length(s) for s in strokes]
    gap = lift * sum(lens) / max(len(lens), 1)
    total = sum(lens) + gap * max(len(lens) - 1, 0)
    at = vb.clamp01(p) * total
    tip = None
    for s, n in zip(strokes, lens):
        if at <= 0:
            break
        part = s if at >= n else vb.paths.reveal(s, at / n)
        if len(part) >= 2:
            _stroke(cv, part, color, width, alpha)
        if 0 < at < n:
            tip = part[-1]
        at -= n + gap
    if tip and nib:
        demo.dot(cv, tip[0], tip[1], r=width * 0.9, color=nib, alpha=alpha)
    return tip


# The demo's word, "hello" in a joined hand: control points in x-height units
# (baseline y = 0, x-height y = -1, ascenders y = -2.4), one continuous stroke.
_HELLO = (
    (-0.6, 0.15), (0.0, -0.5), (0.5, -1.7), (0.45, -2.4), (0.1, -2.0), (0.2, -0.8), (0.12, 0.0),  # h stem
    (0.35, -0.75), (0.75, -0.95), (0.95, -0.55), (0.98, 0.0),                                   # h hump
    (1.35, -0.25), (1.85, -0.55), (1.9, -0.95), (1.6, -0.95), (1.45, -0.5), (1.65, -0.02),      # e
    (2.1, -0.3), (2.65, -1.6), (2.7, -2.4), (2.35, -2.2), (2.3, -1.0), (2.45, -0.02),            # l
    (2.95, -0.4), (3.5, -1.6), (3.55, -2.4), (3.2, -2.2), (3.15, -1.0), (3.3, -0.02),          # l
    (3.6, -0.5), (4.0, -1.0), (3.65, -0.75), (3.7, -0.08), (4.05, -0.2), (4.2, -0.75),          # o
    (4.0, -1.0), (4.35, -0.85), (4.95, -0.9),                                                   # tie-off
)


def _hello(x, y, size):
    """The demo word placed with its baseline start at (x, y), `size` px per x-height."""
    pts = [(x + u * size, y + v * size) for u, v in _HELLO]
    return [vb.paths.jitter(smooth(pts), seed=3, amount=1.2, wander=0.2)]


def draw(n, cv):
    size = 72
    strokes = _hello(demo.W / 2 - 2.2 * size, demo.H / 2 + 1.0 * size, size)
    demo.floor(cv, demo.H / 2 + 1.0 * size + 14, color=demo.LINE)
    write_on(cv, strokes, demo.phase(n, 0.3, 2.5), demo.INK, width=7, nib=demo.ACCENT)
    cv.mark('word', demo.W / 2 - 2.9 * size, demo.H / 2 - 1.5 * size, 5.8 * size, 2.6 * size)


CAPABILITY = Capability(
    id='handwriting-reveal',
    name='Handwriting reveal',
    family='typography',
    group='Stroke and outline',
    aliases=('write-on', 'handwritten text animation', 'signature reveal', 'script write-on'),
    definition='A word draws itself in as though a pen were writing it, the ink line growing along each '
               'letter in the order a hand would make it.',
    phrasings=('make the title look like someone is writing it by hand',
               'animate the signature being signed',
               'the cursive word writes itself onto the screen'),
    related=('brush-stroke-paint-reveal', 'text-mask-reveal', 'ink-spread-reveal', 'typewriter-reveal',
             'wipe-reveal', 'line-draw-logo-reveal'),
    api=('videobuilder.capabilities.typography.handwriting_reveal.write_on',
         'videobuilder.capabilities.typography.handwriting_reveal.smooth',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)

"""Scanline wipe: the incoming scene is drawn in thin horizontal lines, like a
raster beam painting a screen. Every other line sweeps in from top to
bottom, then the lines between them fill the gaps on a second pass."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def scanline_wipe(cv, a, b, p, line=18, overlap=0.15, spread=0.3, beam='#fff6dc'):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` underneath, `b(cv)`
    showing through rows `line` px tall. The even rows sweep top to bottom over
    the first half, the odd rows over the second (the two passes overlap by
    `overlap`). Each row draws left to right over `spread` of its pass, with a
    bright `beam` tip at its leading edge.

    In a film, call it while two shots are live in an overlap, e.g.
    `scanline_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    rows = max(2, int(-(-h // line)))
    half = (1 + overlap) / 2
    shown, tips = [], []
    for i in range(rows):
        k = i % 2
        start = k * (1 - half)
        q = vb.clamp01((p - start) / half)              # this row's pass progress
        order = (i // 2) / max(1, (rows - 1) // 2)       # 0 at the top row, 1 at the bottom
        r = vb.clamp01((q - order * (1 - spread)) / spread)
        if r <= 0:
            continue
        x = w * vb.ease_out_quint(r)
        shown.append((i * line, x))
        if x < w - line:
            tips.append((i * line, x))
    a(cv)
    if not shown:
        return
    c = cv.ctx
    c.save()
    for y, x in shown:
        c.rectangle(0, y, x, line)
    c.clip()
    b(cv)
    c.restore()
    for y, x in tips:
        cv.rect(max(0, x - line * 4), y, min(x, line * 4), line, beam, alpha=0.35)
        cv.rect(max(0, x - line * 0.6), y, min(x, line * 0.6), line, beam, alpha=0.9)


TECHNIQUE = Technique(
    id='scanline-wipe',
    name='Scanline wipe',
    family='transitions',
    group='Wipes',
    aliases=('interlace wipe', 'raster wipe', 'line-by-line wipe'),
    definition='The next scene is painted in over the old one as thin horizontal stripes, '
               'every other stripe first and then the gaps between them, like an old screen redrawing.',
    phrasings=('bring the next shot in line by line like a CRT drawing it',
               'reveal the new scene in thin horizontal stripes that fill in',
               'an interlaced, retro-monitor style transition between the scenes'),
    related=('crt-scanlines', 'wipe-reveal', 'area-fill-sweep', 'scroll-scrubbed-frame-sequence',
             'scanline-tear', 'paint-brush-wipe'),
    api=('videobuilder.techniques.transitions.scanline_wipe.scanline_wipe',),
    demo=lambda: demo.two_scenes(scanline_wipe, start=0.7, length=1.6),
)

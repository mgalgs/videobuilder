"""Interlace combing: every other horizontal line of the picture shows the
scene a moment earlier than the lines between them, so anything moving fast
splits along its edges into fine comb teeth, while still things stay clean --
the look of an interlaced video frame shown without deinterlacing."""
import contextlib

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


@contextlib.contextmanager
def _field_clip(cv, parity, line, x, y, w, h):
    """Clip to every other `line`-tall strip of (x, y, w, h): the strips with
    index parity `parity` (0 = the first, 2, 4, ...; 1 = the rest)."""
    c = cv.ctx
    c.save()
    top, i = y, 0
    while top < y + h:
        if i % 2 == parity:
            c.rectangle(x, top, w, min(line, y + h - top))
        top += line
        i += 1
    c.clip()
    try:
        yield cv
    finally:
        c.restore()


def interlace_combing(cv, scene, t, gap, line=3, x=0, y=0, w=None, h=None, background=None):
    """Draw `scene(cv, t)` as an interlaced frame: the region (x, y, w, h)
    (default the whole frame) is cut into `line`-px horizontal strips; odd
    strips show the scene at time `t`, even strips show it at `t - gap`. The
    further something moves in `gap`, the longer its comb teeth; at `gap` 0 it
    is `scene(cv, t)` untouched. `background`, if given, fills each field
    first, for a scene that does not paint its own background.

    In a film, `gap` is about one field (half a frame), e.g.
    `interlace_combing(cv, lambda c, t: shot(c, t), f.t, 0.5 / fps)`; push it
    larger for a stylised, chunkier comb."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    if gap == 0:
        scene(cv, t)
        return
    for parity, when in ((0, t - gap), (1, t)):
        with _field_clip(cv, parity, line, x, y, w, h):
            if background is not None:
                cv.rect(x, y, w, h, background)
            scene(cv, when)


def _x(t):
    """The demo dot's x at `t` seconds: rests, darts right, rests, darts back."""
    left, right = 220, demo.W - 220
    if t < 1.5:
        p = vb.clamp01((t - 0.3) / 0.9)
    else:
        p = 1 - vb.clamp01((t - 1.75) / 0.9)
    s = p * p * (3 - 2 * p)  # smoothstep: fastest mid-move, so the comb peaks there
    return left + (right - left) * s


def _scene(cv, t):
    cv.fill(demo.BG)
    cy = demo.H / 2
    demo.dot(cv, _x(t), cy - 20, r=86, color=demo.ACCENT)
    demo.word(cv, 'still text stays clean', demo.W / 2, demo.H - 70, size=30, color=demo.MUTED, weight=600)


def draw(n, cv):
    t = n / demo.FPS
    # a stylised field gap of ~2.5 frames, so the teeth read at gallery size
    interlace_combing(cv, _scene, t, gap=2.5 / demo.FPS, line=4)
    cv.mark('dot', _x(t) - 86, demo.H / 2 - 106, 172, 172)


CAPABILITY = Capability(
    id='interlace-combing',
    name='Interlace combing',
    family='vfx',
    group='VHS & tape',
    aliases=('interlace lines', 'field combing', 'combing artifacts', 'interlaced look'),
    definition='Alternate horizontal lines of the frame lag a split second behind the others, so the edges '
               'of anything moving fast break into thin jagged teeth like the tines of a comb.',
    phrasings=('make the fast motion look like old interlaced TV footage with those striped edges',
               'give the moving object jagged line-by-line fringes on its sides, like a badly deinterlaced video',
               'an interlacing artifact where every other row trails behind'),
    related=('line-weave', 'frame-interpolation', 'cross-zoom', 'isolines-contour-animation', 'morph-cut',
             'speed-lines'),
    api=('videobuilder.capabilities.vfx.interlace_combing.interlace_combing',),
    demo=lambda: demo.film(draw),
)

"""Morph Cut: a jump cut between two takes of the same subject, smoothed over
by warping each take so the subject lines up and dissolving between them, so
the subject seems to glide from where it was to where it is."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _ease(t):
    return t * t * (3 - 2 * t)


def _warped(cv, scene, src, dst, alpha):
    """`scene(cv)` drawn with the box `src` stretched onto the box `dst`, at `alpha`."""
    c = cv.ctx
    c.save()
    c.push_group()
    c.translate(dst[0], dst[1])
    c.scale(dst[2] / src[2], dst[3] / src[3])
    c.translate(-src[0], -src[1])
    scene(cv)
    c.pop_group_to_source()
    c.paint_with_alpha(alpha)
    c.restore()


def morph_cut(cv, a, b, p, a_box, b_box):
    """Draw the morph cut at progress `p` (0 -> 1) from `a(cv)` to `b(cv)`.
    `a_box` and `b_box` are (x, y, w, h): where the subject sits in each take.
    Both takes are warped so their subject lands on a box gliding from
    `a_box` to `b_box`, and `b` dissolves in over `a`; at 0 it is exactly `a`,
    at 1 exactly `b`. The unwarped takes, dissolved, fill any edge the warp
    pulls in from the frame.

    In a film, call it across a short overlap at the jump, e.g.
    `morph_cut(cv, take1, take2, f / overlap_frames, (500, 300, 300, 600), (620, 260, 360, 720))`."""
    t = _ease(vb.clamp01(p))
    mid = tuple(x + (y - x) * t for x, y in zip(a_box, b_box))
    a(cv)
    _warped(cv, b, (0, 0, cv.width, cv.height), (0, 0, cv.width, cv.height), t)
    _warped(cv, a, a_box, mid, 1.0)
    _warped(cv, b, b_box, mid, t)


# The demo: two takes of a presenter, the second closer, further right and
# with a hand raised -- a jump cut the morph turns into one smooth move.
TAKE_A = (demo.W * 0.34, demo.H - 353, 200, 373)
TAKE_B = (demo.W * 0.52, demo.H - 447, 250, 467)


def _presenter(cv, box, hand_up):
    x, y, w, h = box
    u = w / 300  # the figure is drawn in a 300 x 560 box, scaled to fit
    cv.fill(demo.BG)
    cx = x + w / 2
    body = (x + 20 * u, y + 230 * u, 260 * u, 330 * u)
    if hand_up:
        cv.line(cx + 110 * u, y + 270 * u, cx + 175 * u, y + 120 * u, demo.TEAL, width=46 * u)
        demo.dot(cv, cx + 178 * u, y + 108 * u, r=30 * u, color='#e8c2a0')
    cv.rect(*body, demo.TEAL, radius=90 * u)
    cv.rect(cx - 30 * u, y + 200 * u, 60 * u, 50 * u, '#d9b08c')
    demo.dot(cv, cx, y + 120 * u, r=100 * u, color='#e8c2a0')
    cv.sector(cx, y + 110 * u, 104 * u, 3.3, 6.12, '#3b2b24')   # hair
    demo.dot(cv, cx - 34 * u, y + 130 * u, r=9 * u, color=demo.BG)
    demo.dot(cv, cx + 34 * u, y + 130 * u, r=9 * u, color=demo.BG)
    cv.arc(cx, y + 160 * u, 30 * u, 0.4 if hand_up else 0.8, 2.7 if hand_up else 2.3, demo.BG, width=7 * u)
    cv.mark('presenter', x, y, w, h)


def take_a(cv):
    _presenter(cv, TAKE_A, False)


def take_b(cv):
    _presenter(cv, TAKE_B, True)


TECHNIQUE = Technique(
    id='morph-cut',
    name='Morph cut',
    family='transitions',
    group='Cuts',
    aliases=('jump-cut morph', 'morphing cut'),
    definition='Where a jump cut would make the subject pop to a new spot, the two shots are warped '
               'into line and blended so the subject seems to slide smoothly across the edit.',
    phrasings=('hide the jump cut so it looks like one continuous take',
               'smooth out the cut where I trimmed the pause in the interview',
               'blend the two clips so the speaker does not jump'),
    related=('shape-morph', 'shape-boolean-merge', 'whip-pan', 'isolines-contour-animation',
             'cut-out-paper-animation', 'play-pause-morph'),
    api=('videobuilder.techniques.transitions.morph_cut.morph_cut',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: morph_cut(cv, a, b, p, TAKE_A, TAKE_B),
                                 start=0.9, length=1.2, a=take_a, b=take_b),
)

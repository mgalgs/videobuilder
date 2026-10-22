"""Jump Cut: one locked-off shot is cut so the subject snaps from one place
to another while everything around it stays put, and the edit reads as
skipped time."""
from .. import _demo as demo
from ..schema import Technique


def jump_cut(cv, a, b, p, at=0.5):
    """Draw the cut at progress `p` (0 -> 1): `a(cv)` until `at`, then `b(cv)`,
    with nothing in between. `a` and `b` should be the same framing with the
    subject moved, which is what makes a hard cut read as a jump.

    In a film, call it across the overlap of two takes, e.g.
    `jump_cut(cv, lambda c: shot(c, take1), lambda c: shot(c, take2), new.f / overlap_frames)`."""
    (a if p < at else b)(cv)


def jump_cuts(cv, shot, takes, p):
    """Draw a run of jump cuts at progress `p` (0 -> 1) through the shot:
    `shot(cv, take, q)` for the take whose equal slice of the run `p` falls
    in, `q` running 0 -> 1 within that take. `takes` are whatever `shot`
    needs to place the subject (positions, poses), one per take."""
    n = len(takes)
    i = min(n - 1, max(0, int(p * n)))
    shot(cv, takes[i], min(1.0, max(0.0, p * n - i)))


# The demo: a fixed room with a standing figure; each take moves the figure and
# advances the recording clock, nothing else changes.
FLOOR = demo.H * 0.78
TAKES = ((0.36, 1.00, '00:04'), (0.66, 0.94, '01:37'), (0.48, 1.06, '04:12'), (0.74, 1.00, '07:55'))


def _room(cv, take, q):
    x, scale, clock = take
    cv.fill('#1b1f27')
    # fixed props: a framed picture, a lamp, the floor -- they never move
    cv.rect(demo.W * 0.1, demo.H * 0.2, 150, 100, demo.LINE, radius=6)
    img = demo.photo()
    cv.image(img, demo.W * 0.1 + 8, demo.H * 0.2 + 8, 134, 84)
    lx = demo.W * 0.88
    cv.line(lx, FLOOR, lx, FLOOR - 200, demo.MUTED, width=4)
    cv.sector(lx, FLOOR - 200, 40, 3.1416, 2 * 3.1416, '#e8c872')
    demo.floor(cv, FLOOR)
    # the subject: a figure standing on the floor, breathing slightly within the take
    cx = demo.W * x
    bob = 3 * (q - 0.5)
    body_h, body_w, head = 130 * scale, 76 * scale, 28 * scale
    cv.rect(cx - body_w / 2, FLOOR - body_h + bob, body_w, body_h - bob, demo.TEAL, radius=body_w / 2.4)
    demo.dot(cv, cx, FLOOR - body_h - head * 1.15 + bob, r=head, color=demo.ACCENT)
    # the recording clock in the corner skips ahead at every cut
    demo.dot(cv, 40, 36, r=7, color='#e5484d')
    demo.word(cv, clock, 92, 36, size=24, color=demo.INK, font=demo.mono(24, 600))


TECHNIQUE = Technique(
    id='jump-cut',
    name='Jump cut',
    family='transitions',
    group='Cuts',
    aliases=('jump edit',),
    definition='The camera stays fixed on one shot, but the edit cuts straight to a moment later, '
               'so the subject pops to a new spot while the rest of the frame stays put.',
    phrasings=('cut out the boring bits so the person just jumps between spots',
               'chop the same shot so it skips ahead in time',
               'vlog-style cuts where the subject snaps around the frame'),
    related=('delay', 'tracking-shot', 'cut-to-the-beat', 'strobe-cut', 'punch-in', 'interruptible-motion'),
    api=('videobuilder.techniques.transitions.jump_cut.jump_cut',
         'videobuilder.techniques.transitions.jump_cut.jump_cuts'),
    demo=lambda: demo.film(lambda n, cv: jump_cuts(cv, _room, TAKES, n / (demo.FPS * demo.SECONDS))),
)

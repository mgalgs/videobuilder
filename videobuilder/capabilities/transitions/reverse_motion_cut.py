"""Reverse Motion Cut: the outgoing shot plays forward, then runs backwards
into the edit, and the incoming shot picks up moving the reversed way."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rewind_time(p, turn=0.45, cut=0.7, speed=1.5):
    """The outgoing shot's own time (0 -> 1 is its forward run) at progress
    `p`: forward until `turn`, then playing backwards `speed` times as fast
    until the `cut`, where it holds the frame the edit lands on; never
    earlier than 0."""
    if p < turn:
        return p / turn
    return max(0.0, 1 - speed * (min(p, cut) - turn) / turn)


def _rewind_look(cv, strength, p):
    """A tape-rewind cue over the frame: a cool wash, a few rolling tracking
    lines and a double left-pointing arrow in the top right."""
    w, h = cv.width, cv.height
    cv.fill('#0d2a3a', alpha=0.22 * strength)
    for i in range(4):
        y = ((i * 0.27 + p * 3.1) % 1.0) * h
        cv.rect(0, y, w, h * 0.012, '#ffffff', alpha=0.10 * strength)
    c = cv.ctx
    c.set_source_rgba(*vb.rgba('#ffffff', 0.9 * strength))
    s = h * 0.035
    x0, y0 = w - h * 0.06 - 4 * s, h * 0.06
    for k in range(2):
        x = x0 + k * 2 * s
        c.move_to(x, y0 + s)
        c.line_to(x + 2 * s, y0)
        c.line_to(x + 2 * s, y0 + 2 * s)
        c.close_path()
        c.fill()


def reverse_motion_cut(cv, a, b, p, turn=0.45, cut=0.7, speed=1.5, look=True):
    """Draw the cut at progress `p` (0 -> 1). Unlike a plain transition the
    scenes take a time: `a(cv, t)` and `b(cv, t)` draw their shot at its own
    `t` (0 -> 1). Shot A plays forward until `turn`, then rewinds (see
    `rewind_time`) with an optional tape-rewind `look`; at `cut` it hard-cuts
    to B, which plays forward from 0 over the rest. Give B motion in the
    rewound direction so the movement carries across the edit.

    In a film, call it across the span the two shots share, e.g.
    `reverse_motion_cut(cv, lambda c, t: shot_a(c, t), lambda c, t: shot_b(c, t), f / span_frames)`."""
    if p < cut:
        a(cv, rewind_time(p, turn, cut, speed))
        if look and p > turn:
            _rewind_look(cv, min(1.0, (p - turn) / 0.04), p)
    else:
        b(cv, (p - cut) / (1 - cut))


def shot_a(cv, t):
    """Demo outgoing shot: a card sliding left to right along a floor."""
    cv.fill(demo.BG)
    demo.floor(cv, demo.H / 2 + 120)
    demo.card(cv, 300 + (demo.W - 600) * t, demo.H / 2 + 30, color=demo.ACCENT)
    demo._label(cv, 'A')


def shot_b(cv, t):
    """Demo incoming shot: a card arriving from the right, still moving left, settling centre."""
    cv.fill('#e9e6df')
    x = demo.W / 2 + (demo.W / 2 + 200) * (1 - vb.ease_out_quint(t))
    demo.card(cv, x, demo.H / 2, w=360, h=220, color=demo.TEAL)
    demo._label(cv, 'B', ink=demo.BG)


def draw(n, cv):
    # Turn at 1.45 s, cut at 2.25 s while A is still rewinding (t ~ 0.04), so
    # the gallery poster (2.1 s) lands mid-rewind with the tape cue up; B then
    # has 0.45 s to settle and holds to the end.
    reverse_motion_cut(cv, shot_a, shot_b, demo.phase(n, 0.2, 2.7), turn=0.5, cut=0.82)


CAPABILITY = Capability(
    id='reverse-motion-cut',
    name='Reverse motion cut',
    family='transitions',
    group='Cuts',
    aliases=('reverse cut', 'backwards cut', 'rewind cut'),
    definition='The first shot runs forward, then suddenly rewinds, and the edit lands on the next shot '
               'while the movement is going backwards.',
    phrasings=('rewind the clip right before we cut to the next one',
               'make it look like the tape runs backwards into the cut',
               'play the end of the shot in reverse and then jump to the next scene'),
    related=('reverse-playback', 'interruptible-motion', 'reverse-cymbal', 'flip', 'tracking-shot', 'push'),
    api=('videobuilder.capabilities.transitions.reverse_motion_cut.reverse_motion_cut',
         'videobuilder.capabilities.transitions.reverse_motion_cut.rewind_time'),
    demo=lambda: demo.film(draw),
)

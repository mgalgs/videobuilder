"""Stutter Cut: just before the cut, the outgoing shot snaps back and replays
its last few frames a few times over, catching like a skipping record, then
the incoming shot cuts in hard."""
from .. import _demo as demo
from ..schema import Technique


def stutter_progress(p, cut=0.8, repeats=3, span=0.1):
    """The outgoing shot's own progress to show at transition progress `p`
    (0 -> 1). It runs straight up to `cut - repeats * span`, then replays the
    `span` just before that point `repeats` times, each replay jumping back
    to the same frame. Past `cut` it holds where the stutter ended."""
    start = cut - repeats * span
    if p < start:
        return p
    if p >= cut:
        return start
    return start - span + (p - start) % span


def stutter_cut(cv, a, b, p, cut=0.8, repeats=3, span=0.1, punch=0.04):
    """Draw the stutter at progress `p` (0 -> 1): `a(cv, s)` with its own
    progress `s` from `stutter_progress`, then from `cut` on, `b(cv)` with no
    blend. Every other replay is pushed in by `punch` about the frame's
    centre, so the repeats read even when `a` moves little.

    Unlike a plain transition, `a` takes the progress it should show, so its
    motion can be replayed; in a film map `s` back onto the shot's own clock,
    e.g. `stutter_cut(cv, lambda c, s: scene_a(c, t0 + s * overlap), lambda c: scene_b(c, new), p)`."""
    if p >= cut:
        b(cv)
        return
    start = cut - repeats * span
    k = 1.0
    if p >= start and int((p - start) / span) % 2 == 0:
        k += punch
    with cv.layer(dx=cv.width / 2 * (1 - k), dy=cv.height / 2 * (1 - k), scale=k):
        a(cv, stutter_progress(p, cut, repeats, span))


def scene_a(cv, s):
    """The demo's outgoing shot: a card sliding left to right across the frame."""
    cv.fill(demo.BG)
    demo.floor(cv, demo.H / 2 + 150)
    demo.card(cv, demo.W * (0.15 + 1.2 * s), demo.H / 2)
    demo.word(cv, 'Scene A', 120, 52, size=28)


def draw(n, cv):
    stutter_cut(cv, scene_a, demo.scene_b, demo.phase(n, 0.2, 2.4), span=0.12)


TECHNIQUE = Technique(
    id='stutter-cut',
    name='Stutter cut',
    family='transitions',
    group='Cuts',
    aliases=('stutter edit', 'frame repeat cut'),
    definition='Right before the edit, the outgoing shot jumps back and replays the same split second '
               'a few times in a row, then the next shot cuts in.',
    phrasings=('make the clip skip and repeat a few times before it cuts',
               'a glitchy stutter on the last frames, then hard cut to the next scene',
               'repeat the end of the shot like a skipping record before switching'),
    related=('frame-stutter', 'zoom-blur', 'wiggle-path', 'glitch-transition', 'scanline-jitter', 'rack-focus'),
    api=('videobuilder.techniques.transitions.stutter_cut.stutter_cut',
         'videobuilder.techniques.transitions.stutter_cut.stutter_progress'),
    demo=lambda: demo.film(draw),
)

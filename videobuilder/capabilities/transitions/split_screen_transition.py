"""Split-screen Transition: the incoming scene pushes in as a second panel,
the frame holds split between the two scenes for a beat, then the incoming
panel pushes the outgoing one off."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def split_screen_transition(cv, a, b, p, hold=0.3, split=0.5, gap=8, color='#000000',
                            ease=vb.ease_in_out_quart):
    """Draw the split at progress `p` (0 -> 1): `b(cv)` pushes in from the
    right until the frame is divided at `split` of its width, both panels
    hold for the middle `hold` fraction, then `b` pushes `a(cv)` off the
    left. Each panel shows its scene centred in it, and a `gap`-wide bar of
    `color` divides them.

    In a film, call it while two shots are live in an overlap, e.g.
    `split_screen_transition(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    move = (1 - hold) / 2
    x = vb.interpolate(p, (0, move, move + hold, 1), (w, w * split, w * split, 0), ease=ease)
    if x > 0:
        with cv.clip(0, 0, x, h), cv.layer(dx=x / 2 - w / 2):
            a(cv)
    if x < w:
        with cv.clip(x, 0, w - x, h), cv.layer(dx=x / 2):
            b(cv)
    if 0 < x < w and gap > 0:
        cv.rect(x - gap / 2, 0, gap, h, color)


CAPABILITY = Capability(
    id='split-screen-transition',
    name='Split-screen transition',
    family='transitions',
    group='Slides and Pushes',
    aliases=('split-screen push', 'split wipe', 'side-by-side transition'),
    definition='The next scene slides in beside the current one so both share the frame for a moment, '
               'then it slides on across until it fills the screen.',
    phrasings=('bring the new shot in next to the old one, hold both, then let it take over',
               'show the two scenes side by side for a beat on the way from one to the other',
               'push the next clip in halfway, pause on the split, then finish the push'),
    related=('split-screen-comparison', 'view-transition', 'barn-door-wipe', 'shutter-wipe',
             'curtain-reveal', 'split-flap-display'),
    api=('videobuilder.capabilities.transitions.split_screen_transition.split_screen_transition',),
    demo=lambda: demo.two_scenes(split_screen_transition, start=0.5, length=2.1),
)

"""Strobe cut: a run of bright flashes, each one cutting the picture to the
other scene, so the two flicker back and forth before the incoming scene
stays.

Mind photosensitive viewers: keep the flashes at most three in any one
second (`check.py --video` counts them), i.e. a transition of `flashes`
pulses should last more than `flashes / 3` seconds."""
from .. import _demo as demo
from ..schema import Technique


def strobe_cut(cv, a, b, p, flashes=5, decay=0.6, color='#ffffff'):
    """Draw the strobe at progress `p` (0 -> 1): `flashes` evenly spaced
    pulses of `color`, each hitting full strength and cutting to the other
    scene, then fading over the first `decay` of its slot. The last pulse
    always lands on `b(cv)`, so the scenes alternate backwards from there.

    In a film, call it while two shots are live in an overlap, e.g.
    `strobe_cut(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    t = min(max(p, 0.0), 1.0) * flashes
    i = min(int(t), flashes - 1)
    q = t - i
    (b if (flashes - 1 - i) % 2 == 0 else a)(cv)
    if q < decay:
        cv.fill(color, alpha=(1 - q / decay) ** 2)


def _demo():
    # 5 pulses over 1.8 s: one every 0.36 s, under three a second.
    return demo.two_scenes(strobe_cut, start=0.6, length=1.8)


TECHNIQUE = Technique(
    id='strobe-cut',
    name='Strobe cut',
    family='transitions',
    group='Light and Flash',
    aliases=('strobe transition', 'rapid flash', 'strobe flash', 'stroboscopic cut'),
    definition='A quick burst of white flashes flips the picture back and forth between the old '
               'and new scenes, and when the flashing stops the new scene is left on screen.',
    phrasings=('flicker between the two shots with bright flashes, then land on the second',
               'a strobe-light transition into the next scene',
               'flash white a few times, swapping scenes on each flash'),
    related=('lightning-flash', 'smash-cut', 'cut-on-action', 'morph-cut', 'whip-pan', 'zoom-blur'),
    api=('videobuilder.techniques.transitions.strobe_cut.strobe_cut',),
    demo=_demo,
)

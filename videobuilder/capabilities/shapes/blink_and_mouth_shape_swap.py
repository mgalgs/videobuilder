"""Blink and mouth shape swap: a simple face comes alive by replacing whole
drawings outright -- open eyes for shut ones for a few frames, and one mouth
shape for the next -- with no in-between, the way cut-out and limited
animation fakes blinking and talking."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

MOUTHS = ('rest', 'smile', 'o', 'open', 'wide')


def blinking(t, at=(), length=0.12):
    """True while the eyes should be shut: within `length` seconds after any
    blink time in `at` (seconds)."""
    return any(b <= t < b + length for b in at)


def mouth_at(t, shapes, start=0.0, hold=0.1, rest='rest'):
    """The mouth shape at time `t` for a talking track: `shapes` (names from
    `MOUTHS`) swap in one after another from `start`, each held `hold`
    seconds; before and after the track the mouth is `rest`."""
    i = math.floor((t - start) / hold)
    return shapes[i] if 0 <= i < len(shapes) else rest


def _oval(cv, cx, cy, w, h, color):
    cv.rect(cx - w / 2, cy - h / 2, w, h, color, radius=min(w, h) / 2)


def draw_eye(cv, cx, cy, r, shut=False, color=demo.BG):
    """One eye of a face of radius `r`: a tall oval, or a short downward
    curve when `shut`."""
    if shut:
        cv.arc(cx, cy - r * 0.06, r * 0.1, 0.12 * math.pi, 0.88 * math.pi, color, width=r * 0.035)
    else:
        _oval(cv, cx, cy, r * 0.11, r * 0.2, color)


def draw_mouth(cv, cx, cy, r, shape='rest', color=demo.BG):
    """The mouth of a face of radius `r`, as one of `MOUTHS`: a flat line,
    a smile, a small O, an open oval, or a wide grin-shaped opening."""
    if shape == 'rest':
        cv.rect(cx - r * 0.17, cy - r * 0.025, r * 0.34, r * 0.05, color, radius=r * 0.025)
    elif shape == 'smile':
        cv.arc(cx, cy - r * 0.18, r * 0.24, 0.2 * math.pi, 0.8 * math.pi, color, width=r * 0.045)
    elif shape == 'o':
        _oval(cv, cx, cy, r * 0.13, r * 0.18, color)
    elif shape == 'open':
        _oval(cv, cx, cy + r * 0.03, r * 0.24, r * 0.3, color)
    elif shape == 'wide':
        cv.rect(cx - r * 0.24, cy - r * 0.07, r * 0.48, r * 0.16, color, radius=r * 0.08)
    else:
        raise ValueError(f'unknown mouth shape {shape!r}; shapes are {", ".join(MOUTHS)}')


def draw_face(cv, cx, cy, r, shut=False, mouth='rest', skin=demo.ACCENT, ink=demo.BG):
    """A round face of radius `r` centred at (cx, cy), eyes shut or open and
    mouth in shape `mouth`. Call it each frame with `blinking` and `mouth_at`
    to make it blink and talk. Returns the face's Box."""
    demo.dot(cv, cx, cy, r, skin)
    for side in (-1, 1):
        draw_eye(cv, cx + side * r * 0.33, cy - r * 0.15, r, shut, ink)
    draw_mouth(cv, cx, cy + r * 0.38, r, mouth, ink)
    return vb.Box(cx - r, cy - r, 2 * r, 2 * r)


TALK = ('open', 'o', 'wide', 'rest', 'open', 'o', 'wide', 'open', 'rest', 'o', 'open', 'wide')


def draw(n, cv):
    t = n / demo.FPS
    shut = blinking(t, at=(0.35, 2.45), length=0.15)
    mouth = mouth_at(t, TALK, start=0.8, hold=0.1, rest='rest' if t < 0.8 else 'smile')
    box = draw_face(cv, demo.W / 2, demo.H / 2 - 30, 160, shut, mouth)
    cv.mark('face', *box)
    demo.word(cv, f'eyes {"shut" if shut else "open"}  ·  mouth {mouth}', demo.W / 2, demo.H / 2 + 175,
              size=22, color=demo.MUTED, font=demo.mono(22, 500))


CAPABILITY = Capability(
    id='blink-and-mouth-shape-swap',
    name='Blink and mouth shape swap',
    family='shapes',
    group='Characters & rigs',
    aliases=('facial expression swap', 'lip sync shapes', 'eye blink cycle', 'mouth chart'),
    definition='A character face blinks and talks by cutting straight between separate drawings of its eyes '
               'and mouth, with no tweening between them.',
    phrasings=('make the cartoon face blink and look like it is talking',
               'swap the mouth shapes so the character lip-syncs',
               'a simple face whose eyes close now and then while its mouth flaps'),
    related=('icon-state-morph', 'glyph-cycling', 'letter-morph', 'julia-set-morph', 'emoji-substitution',
             'text-to-shape-morph'),
    api=('videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.draw_face',
         'videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.blinking',
         'videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.mouth_at'),
    demo=lambda: demo.film(draw),
)

"""Stereo panning: a sound slides between the left and right speakers to follow
the thing making it across the screen. `stereo_pan(sound, position)` turns one
placed sound (a `vb.sfx` sound, or any `vb.Sound`) into a few overlapping
pieces, each held at its own left/right balance and crossfaded into the next,
so the balance glides with `position(frame)`: -1 hard left, 0 centre, 1 hard
right. The demo sends a dot across the frame on a long whoosh, the two
speakers' meters trading level as it passes.

The mixer has no pan control of its own: it writes each sound's gain into the
sound's ffmpeg chain as `volume=<gain_db>dB`, so a piece's gain here is a
`Balance`, a dB float that writes a `pan` filter after its volume there.
A film with more than `videobuilder.render.PREMIX_OVER` sound effects in all
mixes them in-process instead (`videobuilder.stem`), where the gain holds and
the balance is lost: keep a panned film's effects under that.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pan_gains(position):
    """(left, right) gains for `position` in [-1, 1], equal-power: about 0.71
    each at the centre, so a sound keeps its loudness as it crosses."""
    angle = (max(-1.0, min(1.0, position)) + 1) * math.pi / 4
    return math.cos(angle), math.sin(angle)


class Balance(float):
    """A gain in dB that also carries a left/right balance. It is the dB as a
    number everywhere, and in the mixer's `volume=...dB` it adds a mono fold
    and a `pan` to those gains (the dB after it is a second volume of 0)."""

    def __new__(cls, db, left, right):
        g = super().__new__(cls, float(db))
        g.left, g.right = left, right
        return g

    def __format__(self, spec):
        if spec:
            return float.__format__(self, spec)
        l, r = self.left / 2, self.right / 2
        return (f'{float(self)!r}dB,aformat=channel_layouts=stereo,'
                f'pan=stereo|c0={l:.5f}*c0+{l:.5f}*c1|c1={r:.5f}*c0+{r:.5f}*c1,volume=0')

    def __reduce__(self):
        return Balance, (float(self), self.left, self.right)


def stereo_pan(sound, position, fps=30, pieces=12):
    """`sound` (a `vb.sfx.sound(...)` or any `vb.Sound`) panned by `position`:
    a number in [-1, 1] (-1 hard left), or `position(frame)` giving one for a
    film frame, to follow something across the screen. Returns a tuple of
    `vb.Sound`s for the film's `sounds`: at most `pieces + 1` overlapping
    pieces of it, each at the balance of its middle frame, crossfaded
    linearly so the balance glides between them. `fps` is the film's."""
    if hasattr(sound, 'at_fps'):
        sound = sound.at_fps(fps)
    at = position if callable(position) else (lambda frame: position)
    end = sound.at + sound.frames
    step = max(1, math.ceil(sound.frames / pieces))
    middles = list(range(sound.at, end - 1, step)) or [sound.at]
    out = []
    for k, mid in enumerate(middles):
        first = middles[k - 1] if k else sound.at
        last = middles[k + 1] if k + 1 < len(middles) else end
        out.append(vb.Sound(sound.path, at=first, start=sound.start + (first - sound.at) / fps,
                            frames=last - first, gain_db=Balance(sound.gain_db, *pan_gains(at(mid))),
                            fade_in_frames=mid - first if k else sound.fade_in_frames,
                            fade_out_frames=last - mid if k + 1 < len(middles) else sound.fade_out_frames,
                            ducks=sound.ducks))
    return tuple(out)


# ---- the demo: a dot crosses the frame, its whoosh following it speaker to speaker ----
START, END = 0.6, 2.6            # seconds: the dot's crossing
EDGE = 200                       # how far in from each side it starts and stops
TRACK_Y = 215
SPEAKER_Y = 370


def dot_x(frame):
    p = vb.bezier(0.45, 0, 0.55, 1)(demo.phase(frame, START, END))   # a gentle ease in and out
    return EDGE + (demo.W - 2 * EDGE) * p


def balance(frame):
    """The dot's place across the frame as a pan position, -1 at its left stop, 1 at its right."""
    return (dot_x(frame) - demo.W / 2) / (demo.W / 2 - EDGE)


def speaker(cv, cx, cy, side, level):
    """A speaker cone facing the middle, its sound waves and a level meter lit by `level` (0..1)."""
    s = -1 if side == 'L' else 1
    cv.rect(cx - 15, cy - 18, 30, 36, demo.MUTED, radius=4)
    c = cv.ctx
    c.new_path()
    for x, y in ((cx - s * 15, cy - 18), (cx - s * 40, cy - 40), (cx - s * 40, cy + 40), (cx - s * 15, cy + 18)):
        c.line_to(x, y)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.MUTED))
    c.fill()
    for i in range(3):   # waves out toward the middle, more of them lit as it gets louder
        lit = vb.clamp01(level * 3 - i)
        a0 = -0.6 if s < 0 else math.pi - 0.6
        cv.arc(cx - s * 20, cy, 48 + 22 * i, a0, a0 + 1.2, demo.ACCENT, width=5, alpha=0.12 + 0.88 * lit)
    demo.word(cv, side, cx, cy + 72, size=30, color=demo.INK)
    x0, w, y = cx - 55, 110, cy + 100
    cv.rect(x0, y, w, 10, demo.LINE, radius=5)
    cv.rect(x0, y, max(10, w * level), 10, demo.ACCENT, radius=5)
    cv.mark(f'speaker {side}', cx - 55, cy - 45, 110, 155)


def draw(n, cv):
    x = dot_x(n)
    left, right = pan_gains(balance(n))
    loud = 0.4 + 0.6 * math.sin(math.pi * demo.phase(n, START - 0.1, END + 0.1))   # the whoosh swells and fades
    cv.line(EDGE, TRACK_Y, demo.W - EDGE, TRACK_Y, demo.LINE, width=3)
    for i in range(1, 7):   # a short trail behind the dot
        demo.dot(cv, dot_x(n - 2 * i), TRACK_Y, 30 - 3 * i, alpha=0.18 - 0.025 * i)
    demo.dot(cv, x, TRACK_Y, 30)
    cv.mark('source', x - 30, TRACK_Y - 30, 60, 60)
    speaker(cv, 130, SPEAKER_Y, 'L', left ** 2 * loud)
    speaker(cv, demo.W - 130, SPEAKER_Y, 'R', right ** 2 * loud)
    demo.word(cv, f'pan {balance(n):+.2f}', demo.W / 2, SPEAKER_Y + 105, size=24, color=demo.MUTED,
              font=demo.mono(24))


def film():
    # a long pass-by whoosh, loudest as the dot crosses the middle, where it moves fastest
    whoosh = vb.sfx.sound('whoosh_fast/tight', at=round((START + END) / 2 * demo.FPS), dur=2.0, gain_db=-4)
    return demo.film(draw, sounds=stereo_pan(whoosh, balance, demo.FPS))


CAPABILITY = Capability(
    id='stereo-panning',
    name='Stereo panning',
    family='sound',
    group='Mixing & editing',
    aliases=('panning', 'left-right movement', 'audio pan', 'auto-pan'),
    definition='A sound drifts from one speaker to the other in step with the thing on screen making it, '
               'so you hear it travel left or right as you watch it go.',
    phrasings=('make the whoosh move from the left speaker to the right as the car drives past',
               'have the sound follow the ball across the screen',
               'pan the audio so it comes from where the object is'),
    related=('pan', 'turntable-rotation', 'spin', 'tilt', 'reverse-playback', 'look-around'),
    api=('videobuilder.capabilities.sound.stereo_panning.stereo_pan',
         'videobuilder.capabilities.sound.stereo_panning.pan_gains',
         'videobuilder.sfx.sound'),
    demo=film,
)

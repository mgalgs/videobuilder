"""Cut to the beat: the picture changes shot exactly on the music's beats,
so every cut lands with a kick and the edit feels played rather than placed.

The beats come from `videobuilder.beats.BeatGrid` (fit one to a real track
with `python -m videobuilder beats song.mp3`); `cut_to_the_beat` picks the
shot for a frame from that grid, `beat_pulse` gives a punch that decays
after each cut, and `beat_sounds` lays a sound effect on every beat."""
import videobuilder as vb
from videobuilder.beats import BeatGrid

from .. import _demo as demo
from ..schema import Technique


def beat_shot(n, grid, every=1):
    """(cut, frames): which cut frame `n` falls in when the picture cuts on
    every `every`-th beat of `grid` (cut 0 starts on beat 0; frames before
    beat 0 count as cut 0), and frames since that cut."""
    k = grid.index(n)
    if k is None:
        return 0, n - grid.lo
    if grid.frame(k) > n:
        k -= 1
    if k < 0:
        return 0, n - grid.lo
    cut = k // every
    return cut, n - grid.frame(cut * every)


def cut_to_the_beat(cv, n, grid, shots, every=1):
    """Draw frame `n` of a sequence that hard-cuts to the next of `shots` on
    every `every`-th beat of `grid`, cycling through them. Each shot is
    `shot(cv, t)`, `t` the frames since its cut. Returns the cut index."""
    cut, t = beat_shot(n, grid, every)
    shots[cut % len(shots)](cv, t)
    return cut


def beat_pulse(n, grid, frames=8):
    """1 on a beat, easing to 0 over the next `frames` frames: a punch to
    scale or flash something with as each beat lands."""
    k = grid.index(n)
    if k is None:
        return 0.0
    if grid.frame(k) > n:
        k -= 1
    if k < 0:
        return 0.0
    t = vb.clamp01((n - grid.frame(k)) / frames)
    return (1 - t) ** 3


def beat_sounds(grid, id, hi, offset=0.0, **kw):
    """`vb.sfx.sound(id, ...)` on every beat of `grid` up to frame `hi`,
    shifted `offset` beats (0.5: on the off-beats). `kw` passes through
    (`gain_db`, `align`, `dur`, `note`)."""
    shift = vb.round_half_up(offset * grid.frames_per_beat)
    return tuple(vb.sfx.sound(id, at=f + shift, fps=grid.fps, **kw)
                 for f in grid.frames(hi=hi) if f + shift <= hi)


# ---- demo ----
GRID = BeatGrid(fps=demo.FPS, bpm=120, zero=6)   # a beat every 15 frames: 6, 21, 36, ...
LAST = round(demo.SECONDS * demo.FPS) - 1
PAPER = '#e9e6df'


def _photo(cv, t):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def _dot(cv, t):
    cv.fill(demo.ACCENT)
    demo.dot(cv, demo.W / 2, demo.H / 2 - 40, r=150, color=demo.INK)


def _card(cv, t):
    cv.fill(PAPER)
    demo.card(cv, demo.W / 2, demo.H / 2 - 40, w=520, h=320, color=demo.TEAL)


def _word(cv, t):
    cv.fill(demo.BG)
    demo.word(cv, 'BEAT', demo.W / 2, demo.H / 2 - 40, size=260, color=demo.ACCENT)


SHOTS = (_dot, _photo, _card, _word)


def _shot(draw, pulse):
    """A shot that punches in as its beat lands."""
    def shot(cv, t):
        with cv.layer(scale=1 + 0.06 * pulse, dx=-demo.W * 0.03 * pulse, dy=-demo.H * 0.03 * pulse):
            draw(cv, t)
    return shot


def _ruler(cv, n):
    """The beat ruler along the bottom: a tick per beat, lit once passed, and
    a playhead, so the cuts can be seen landing on the ticks."""
    x0, x1, y = 160, demo.W - 160, demo.H - 80
    span = lambda f: x0 + (x1 - x0) * f / LAST  # noqa: E731
    cv.rect(0, y - 60, demo.W, 140, demo.BG, alpha=0.85)
    cv.line(x0, y, x1, y, demo.MUTED, width=3)
    for k, f in enumerate(GRID.frames(hi=LAST)):
        hit = f <= n
        cv.rect(span(f) - 6, y - 26, 12, 52, demo.ACCENT if hit else demo.MUTED, radius=6)
        demo.word(cv, str(k % 4 + 1), span(f), y - 44, size=26, color=demo.INK if hit else demo.MUTED)
    cv.rect(span(n) - 2, y - 34, 4, 68, demo.INK)
    f = demo.font(26, 700)
    vb.text.draw(cv, ['120 BPM'], f, 40, y - 14, demo.MUTED)


def draw(n, cv):
    pulse = beat_pulse(n, GRID)
    cut_to_the_beat(cv, n, GRID, [_shot(s, pulse) for s in SHOTS])
    cv.fill('#ffffff', alpha=0.35 * pulse)   # a flash on each beat, so the cut reads as a hit
    _ruler(cv, n)


def demo_film():
    """A kick on every beat and a hat on every off-beat, with the picture
    cutting to a new shot on each kick."""
    kicks = beat_sounds(GRID, 'pro_impact/short', LAST, dur=0.4, gain_db=-6)
    hats = beat_sounds(GRID, 'fit/click/floss_lid', LAST, offset=0.5, gain_db=-10)
    return demo.film(draw, sounds=kicks + hats)


TECHNIQUE = Technique(
    id='cut-to-the-beat',
    name='Cut to the beat',
    family='sound',
    group='Music',
    aliases=('beat sync', 'edit to the beat', 'cutting on the beat', 'synced to the beat', 'on the beat'),
    definition='Each change of shot, and each big move, is placed on a beat of the music so the edit '
               'pulses in time with the track.',
    phrasings=('make the shots change in time with the music',
               'sync the edits to the drum hits',
               'cut on every beat of the song'),
    related=('cut-on-action', 'jump-cut', 'reverse-motion-cut', 'match-cut', 'timing', 'follow-through'),
    api=('videobuilder.techniques.sound.cut_to_the_beat.cut_to_the_beat',
         'videobuilder.techniques.sound.cut_to_the_beat.beat_pulse',
         'videobuilder.techniques.sound.cut_to_the_beat.beat_sounds',
         'videobuilder.beats.BeatGrid'),
    demo=demo_film,
)

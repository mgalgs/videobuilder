"""Kinetic lyric typography: a song's words arrive one cue at a time, each
with its own entrance (slide, drop, pop, slam), a hit of emphasis on the
beat, and its own exit, so the type moves with the music."""
from dataclasses import dataclass

import videobuilder as vb
from videobuilder import impact

from .. import _demo as demo
from ..schema import Capability

ENTER = 0.28   # seconds an entrance takes
EXIT = 0.22    # seconds an exit takes
TRAVEL = 300   # px a slide or drop travels


@dataclass(frozen=True)
class Cue:
    """One lyric word or line on screen from `start` to `end` seconds,
    centred at (`x`, `y`). `enter`/`exit` are a style each: 'slide-left',
    'slide-right', 'drop', 'rise', 'pop', 'slam' or 'fade' ('slam' enters only:
    it lands from big to size). `hit`, if set, is the time of a beat to punch
    on: the word swells and turns `hit_color`, with a short shake."""
    text: str
    start: float
    end: float
    x: float
    y: float
    size: int = 64
    weight: int = 900
    color: str = demo.INK
    enter: str = 'slide-left'
    exit: str = 'fade'
    hit: float = None
    hit_color: str = demo.ACCENT


def _move(style, q, incoming):
    """(dx, dy, scale, alpha) for `style` with `q` running 1 -> 0 as the word
    settles (incoming) or 0 -> 1 as it leaves."""
    d = TRAVEL * q
    sign = -1 if incoming else 1
    if style == 'slide-left':
        return sign * d, 0, 1, 1 - q * 0.6
    if style == 'slide-right':
        return -sign * d, 0, 1, 1 - q * 0.6
    if style == 'drop':
        return 0, sign * d * 0.6, 1, 1 - q
    if style == 'rise':
        return 0, -sign * d * 0.6, 1, 1 - q
    if style == 'pop':
        return 0, 0, 1 - q * 0.85, 1 - q
    if style == 'slam':
        return 0, 0, 1 + q * 2.2, 1 - q * q
    if style == 'fade':
        return 0, 0, 1, 1 - q
    raise ValueError(f'unknown lyric move {style!r}')


def cue_state(cue, t, fps=30):
    """Where `cue` is at `t` seconds: (dx, dy, scale, alpha, color), or None
    when it is off screen."""
    if not cue.start <= t < cue.end:
        return None
    if t < cue.start + ENTER:
        ease = vb.ease_out_back if cue.enter == 'pop' else vb.ease_out_expo
        q = 1 - ease((t - cue.start) / ENTER)
        dx, dy, s, a = _move(cue.enter, q, True)
    elif t > cue.end - EXIT:
        dx, dy, s, a = _move(cue.exit, vb.ease_in_expo((t - (cue.end - EXIT)) / EXIT), False)
    else:
        dx, dy, s, a = 0, 0, 1, 1
    color = cue.color
    if cue.hit is not None:
        k = (t - cue.hit) * fps
        if 0 <= k < 12:
            s *= 1 + 0.18 * (1 - k / 12) ** 2
            sx, sy = impact.shake(round(k), 0, frames=10, amount=9, seed=len(cue.text))
            dx, dy = dx + sx, dy + sy
        if t >= cue.hit:
            color = cue.hit_color
    return dx, dy, s, vb.clamp01(a), color


def draw_lyric(cv, cue, t, fps=30, font=None):
    """Draw `cue` as it is at `t` seconds. Returns its Box, or None when off screen."""
    st = cue_state(cue, t, fps)
    if st is None:
        return None
    dx, dy, s, a, color = st
    f = font or demo.font(cue.size, cue.weight)
    w, h = vb.text.block_size([cue.text], f)
    with cv.layer(opacity=a, dx=dx + cue.x * (1 - s), dy=dy + cue.y * (1 - s), scale=s):
        return vb.text.draw(cv, [cue.text], f, cue.x - w / 2, cue.y - h / 2, color)


def draw_lyrics(cv, cues, t, fps=30):
    """Draw every cue on screen at `t` seconds, in order."""
    for i, cue in enumerate(cues):
        box = draw_lyric(cv, cue, t, fps)
        if box is not None:
            cv.mark(f'lyric-{i}', *box)


CX, CY = demo.W / 2, demo.H / 2
CUES = (
    Cue('WE', 0.1, 1.45, CX - 70, CY - 85, size=52, enter='pop', exit='slide-right'),
    Cue('MOVE', 0.35, 1.5, CX + 20, CY + 5, size=110, color=demo.MUTED, enter='slide-left',
        exit='slide-right', hit=0.85),
    Cue('WITH THE', 1.55, 2.95, CX, CY - 95, size=44, weight=700, enter='drop', exit='fade'),
    Cue('TIDE', 1.85, 2.95, CX, CY + 15, size=140, enter='slam', exit='fade', hit=1.85, hit_color=demo.TEAL),
)


def draw(n, cv):
    draw_lyrics(cv, CUES, n / demo.FPS, demo.FPS)


CAPABILITY = Capability(
    id='kinetic-lyric-typography',
    name='Kinetic lyric typography',
    family='typography',
    group='Lyrics and captions',
    aliases=('lyric video type', 'kinetic type', 'lyric video'),
    definition='Song words appear a few at a time, each flying, dropping or slamming in its own way, '
               'punching on the beat and leaving before the next line takes its place.',
    phrasings=('make a lyric video where the words move to the music',
               'animate the song lyrics so each word comes in differently on the beat',
               'bouncy kinetic text for the chorus, words slamming in time'),
    related=('kinetic-poster-layout', 'impact-shake', 'speed-ramp', 'speed-lines', 'twirl-warp-text',
             'echo-trail-type'),
    api=('videobuilder.capabilities.typography.kinetic_lyric_typography.draw_lyrics',
         'videobuilder.capabilities.typography.kinetic_lyric_typography.Cue',
         'videobuilder.capabilities.typography.kinetic_lyric_typography.draw_lyric',
         'videobuilder.capabilities.typography.kinetic_lyric_typography.cue_state'),
    demo=lambda: demo.film(draw),
)

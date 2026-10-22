"""Reverse Cymbal: a crash played backwards -- a bright wash that rises out
of silence and stops dead on the beat it leads into, usually a cut or a hit."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SWELL = 'riser/swell'   # bright noise from near silence, growing to its peak at its very end
CURVE = 4.5             # how sharply `swell_level` climbs (a crash's decay, run backwards)


def reverse_cymbal(at, dur=2.0, gain_db=-6.0, id=SWELL, fps=30, through=False):
    """The reversed-crash swell as a `vb.sfx` sound whose peak, its last
    instant, lands on film frame `at`: the cut, the hit, the downbeat.

    It takes the bank take whose length is nearest `dur` seconds whole, never
    trimmed, since trimming fades the end and the sudden stop is the point.
    `id` swaps in another build that ends on its peak (`riser/air`,
    `pro_riser/air_gate`). Put it in `vb.Film(sounds=...)`, usually beside a
    hit on the same frame."""
    take = vb.sfx.get(id).nearest_length(dur)
    return take.sound(at, fps=fps, align='peak', gain_db=gain_db, through=through)


def swell_level(n, at, dur=2.0, fps=30, curve=CURVE):
    """How loud the swell is at frame `n`, 0 -> 1: near nothing `dur` seconds
    before frame `at`, climbing steeply to 1 on `at`, and 0 from there on
    (it stops, it doesn't fade). For drawing visuals that follow the sound."""
    if n >= at:
        return 0.0
    u = vb.clamp01(1 - (at - n) / (dur * fps))
    return (math.exp(curve * u) - 1) / (math.exp(curve) - 1)


DUR = 2.0
HIT = round(2.1 * demo.FPS)           # the downbeat: the swell's end and the hit
CX, CY, R = demo.W / 2, demo.H * 0.37, 92
WAVE_Y, WAVE_H = demo.H - 72, 46
X0, X1 = 80, demo.W - 80
T0 = (HIT - DUR * demo.FPS) / demo.FPS  # seconds: when the swell starts


def _cymbal(cv, level, flash):
    """A cymbal face-on: a disc with lathe grooves and a bell, glowing with the swell."""
    glow = level + flash
    for k in range(6, 0, -1):
        demo.dot(cv, CX, CY, R + 9 * k * (0.4 + glow), color=demo.ACCENT, alpha=0.05 * glow)
    demo.dot(cv, CX, CY, R, color='#c9a24a')
    for r in range(int(R * 0.35), R, 10):
        cv.arc(CX, CY, r, 0, 2 * math.pi, '#8f6f2a', width=2, alpha=0.55)
    demo.dot(cv, CX, CY, R * 0.26, color='#e2c070')
    demo.dot(cv, CX, CY, 6, color='#5c4718')
    if glow > 0:
        demo.dot(cv, CX, CY, R, color='#fff6d8', alpha=min(1.0, 0.75 * glow))
    cv.mark('cymbal', CX - R, CY - R, 2 * R, 2 * R)


def _rings(cv, n):
    """Ripples flowing inward and shrinking onto the cymbal: a crash's spread, reversed."""
    if n >= HIT:
        return
    t = n / demo.FPS
    for i in range(5):
        u = ((t - T0) * 0.9 + i / 5) % 1      # 0 far out -> 1 at the rim
        if t - T0 < i / 5 / 0.9:
            continue
        r = R + (1 - u) * 300
        cv.arc(CX, CY, r, 0, 2 * math.pi, demo.ACCENT, width=2 + 4 * u,
               alpha=swell_level(n, HIT, DUR, demo.FPS) * u)


def _waveform(cv, n):
    """The sound's shape across the bottom, drawn up to the playhead: a wash
    that grows and then stops sharply on the hit line."""
    span = (demo.SECONDS * demo.FPS)
    hit_x = X0 + (X1 - X0) * HIT / span
    head = X0 + (X1 - X0) * n / span
    cv.line(X0, WAVE_Y, X1, WAVE_Y, demo.LINE, width=2)
    cv.line(hit_x, WAVE_Y - WAVE_H - 12, hit_x, WAVE_Y + WAVE_H + 12, demo.MUTED, width=2, alpha=0.8)
    step = 6
    x = X0
    while x <= min(head, X1):
        f = (x - X0) / (X1 - X0) * span
        a = swell_level(f, HIT, DUR, demo.FPS)
        jitter = 0.65 + 0.35 * abs(math.sin(x * 12.9898) * 43758.5453 % 1)
        h = WAVE_H * a * jitter
        if abs(x - hit_x) < step:
            h = WAVE_H                          # the hit itself
        if h > 1:
            cv.rect(x - 2, WAVE_Y - h, 4, 2 * h, demo.ACCENT if x < hit_x else demo.TEAL, radius=2)
        x += step
    demo.dot(cv, head, WAVE_Y, 5, color=demo.INK)


def draw(n, cv):
    level = swell_level(n, HIT, DUR, demo.FPS)
    flash = max(0.0, 1 - (n - HIT) / 8) if n >= HIT else 0.0
    _rings(cv, n)
    _cymbal(cv, level, flash)
    if n >= HIT:
        p = demo.phase(n, HIT / demo.FPS, HIT / demo.FPS + 0.35)
        s = vb.ease_out_back(p)
        demo.word(cv, 'DROP', CX, CY, size=max(1, round(52 * s)), color=demo.BG, weight=900)
    _waveform(cv, n)


def _swell_id():
    """The first reversed-crash build this pack has; a stripped-down pack
    (the tests') may only have a short whoosh, still landing on the hit."""
    for id in (SWELL, 'riser/air', 'pro_riser/air_gate', 'whoosh_fast/tight'):
        try:
            vb.sfx.get(id)
            return id
        except ValueError:
            continue
    return SWELL


def _film():
    hit = vb.sfx.sound('pro_impact/short', at=HIT, gain_db=-6)
    return demo.film(draw, sounds=(reverse_cymbal(HIT, DUR, id=_swell_id(), fps=demo.FPS), hit))


TECHNIQUE = Technique(
    id='reverse-cymbal',
    name='Reverse cymbal',
    family='sound',
    group='Sound effects',
    aliases=('reverse crash', 'reversed cymbal', 'reverse cymbal swell'),
    definition='A cymbal crash run backwards, so a bright hiss grows out of silence and cuts off abruptly '
               'right on the beat, cut or hit it is leading into.',
    phrasings=('add that backwards cymbal suck-up right before the logo hits',
               'swell some reversed crash into the drop',
               'give me a whoosh that builds and stops dead on the cut'),
    related=('reverse-playback', 'reverse-motion-cut', 'interruptible-motion', 'ease-out-back', 'flip',
             'ease-in-out-back'),
    api=('videobuilder.techniques.sound.reverse_cymbal.reverse_cymbal',
         'videobuilder.techniques.sound.reverse_cymbal.swell_level',
         'videobuilder.sfx.sound'),
    demo=_film,
)

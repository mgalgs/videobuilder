"""Impact hit: one heavy, punchy sound put exactly on the frame something
lands, slams or strikes, so the picture's moment of contact is felt as well
as seen.

`impact_hit` places a hit from the bundled pack with its peak on the
contact frame, and, if asked, a sub drop starting on the same frame for
weight underneath -- the most a hit should stack:

    LAND = 42
    vb.Film(..., sounds=impact_hit(LAND))
    vb.Film(..., sounds=impact_hit(LAND, sub='pro_sub_drop/quick'))   # heavier

`waveform` draws the sound as a small level meter, a spike on the hit
decaying over its tail, for showing where a hit falls.

The demo drops a heavy block onto a floor: it slams down on one frame, the
frame jolts (`vb.impact.shake`), a shockwave and dust burst out from the
contact, and a meter in the corner spikes with the hit.
"""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def impact_hit(at, id='pro_impact/short', sub=None, fps=30, gain_db=-8.0, sub_gain_db=-12.0,
               sub_dur=1.0):
    """The sounds for one impact on film frame `at`: the pack's hit `id`
    with its peak (its loudest instant) on `at`, and if `sub` names one
    (e.g. 'pro_sub_drop/quick') a sub drop with its onset on `at`, cut to
    `sub_dur` s, for low weight.
    Keep impacts a beat apart; one hit per moment. Returns the placed
    `vb.sfx` sounds, for `Film(sounds=...)`."""
    out = [vb.sfx.sound(id, at=at, fps=fps, gain_db=gain_db)]
    if sub:
        out.append(vb.sfx.sound(sub, at=at, fps=fps, align='onset', dur=sub_dur, gain_db=sub_gain_db))
    return tuple(out)


def hit_level(n, at, fps=30, decay=6.0):
    """The hit's loudness, 0 -> 1, at frame `n` for a hit on frame `at`:
    nothing before it, full on it, dying away exponentially after."""
    if n < at:
        return 0.0
    return math.exp(-decay * (n - at) / fps)


def waveform(cv, x, y, w, h, n, at, fps=30, bars=24, color=demo.ACCENT, idle=demo.LINE, seed=0):
    """A small level meter at (x, y, w, h): `bars` bars that sit low until
    the hit on frame `at`, then spike to full height and decay with it."""
    rnd = random.Random(seed)
    jag = [rnd.uniform(0.55, 1.0) for _ in range(bars)]
    level = hit_level(n, at, fps)
    gap = w / bars
    bw = gap * 0.6
    for i, j in enumerate(jag):
        flicker = 0.75 + 0.25 * math.sin(n * 1.7 + i * 2.3)
        bh = max(4.0, h * j * level * flicker)
        lit = level > 0.05
        cv.rect(x + i * gap, y + (h - bh) / 2, bw, bh, color if lit else idle, radius=bw / 2,
                alpha=0.5 + 0.5 * level if lit else 0.8)
    cv.mark('waveform', x, y, w, h)


# ---- the demo: a heavy block slams onto the floor ----
HIT = round(1.3 * demo.FPS)
FALL = 14                                    # frames of falling before the hit
FLOOR = demo.H * 0.72
BW, BH = 300, 200
CX = demo.W / 2


def _block_y(n):
    """The block's bottom edge: high above, accelerating down, on the floor from the hit."""
    if n >= HIT:
        return FLOOR
    p = vb.clamp01((n - (HIT - FALL)) / FALL)
    return FLOOR - 780 * (1 - p * p)


def _squash(n):
    """(sx, sy) of the block: squashed flat on contact, springing back."""
    k = n - HIT
    if k < 0:
        return 1.0, 1.0
    s = 0.22 * math.exp(-k / 3.5) * math.cos(k * 0.9)
    return 1 + s, 1 - s


def _rings(cv, n):
    k = (n - HIT) / demo.FPS
    for i, delay in enumerate((0.0, 0.08)):   # two shockwave rings, half-ellipses on the floor
        t = k - delay
        if 0 <= t < 0.6:
            r = 90 + 900 * (1 - (1 - t / 0.6) ** 3)
            a = (1 - t / 0.6) ** 2
            c = cv.ctx
            c.save()
            c.translate(CX, FLOOR)
            c.scale(1, 0.28)
            cv.arc(0, 0, r, math.pi, 2 * math.pi, demo.INK if i == 0 else demo.ACCENT, width=10 - 4 * i, alpha=a)
            c.restore()


def _dust(cv, n):
    k = (n - HIT) / demo.FPS
    if k < 0:
        return
    rnd = random.Random(3)
    for _ in range(26):                       # dust kicked out sideways
        side = rnd.choice((-1, 1))
        v = rnd.uniform(250, 900)
        up = rnd.uniform(80, 420)
        x = CX + side * (BW / 2 + v * k)
        y = FLOOR - up * k + 600 * k * k
        if y <= FLOOR and k < 0.9:
            demo.dot(cv, x, y, rnd.uniform(5, 14) * (1 - k / 0.9) + 2, demo.MUTED, alpha=0.8 * (1 - k / 0.9))


def draw(n, cv):
    dx, dy = vb.impact.shake(n, HIT, frames=14, amount=26, seed=1)
    with cv.layer(dx=dx, dy=dy):
        demo.floor(cv, FLOOR)
        _rings(cv, n)
        sx, sy = _squash(n)
        w, h = BW * sx, BH * sy
        bottom = _block_y(n)
        if n < HIT:                              # speed streaks while it drops
            p = vb.clamp01((n - (HIT - FALL)) / FALL)
            if p > 0.3:
                for ox in (-0.3, 0, 0.3):
                    cv.line(CX + ox * BW, bottom - h - 40, CX + ox * BW, bottom - h - 40 - 260 * p, demo.MUTED,
                            width=4, alpha=0.5 * p)
        cv.shadow(CX - w / 2, bottom - h, w, h, radius=16, dy=8, blur=24, color=(0, 0, 0, 0.5))
        cv.rect(CX - w / 2, bottom - h, w, h, demo.TEAL, radius=16)
        demo.word(cv, 'THUD', CX, bottom - h / 2, size=round(64 * min(sx, 1.15)), color=demo.BG, weight=900)
        cv.mark('block', CX - w / 2, bottom - h, w, h)
        _dust(cv, n)
    k = n - HIT
    if 0 <= k < 4:                               # a quick flash on the contact frame
        cv.fill(demo.INK, alpha=0.35 * (1 - k / 4))
    waveform(cv, demo.W - 330, 50, 270, 90, n, HIT, demo.FPS)


def film():
    return demo.film(draw, sounds=impact_hit(HIT, fps=demo.FPS))


CAPABILITY = Capability(
    id='impact-hit',
    name='Impact hit',
    family='sound',
    group='Sound effects',
    aliases=('hit', 'impact', 'thud', 'boom', 'slam', 'punch hit', 'cinematic hit'),
    definition='A short, heavy thump of sound lands on the exact frame something strikes or slams down, '
               'giving the moment of contact physical weight.',
    phrasings=('add a big boom when the box hits the ground',
               'make the logo slam in with a punchy hit sound',
               'put a thud right on the frame where it lands'),
    related=('impact', 'hitstop', 'impact-shake', 'punch-in', 'smash-cut', 'fracture-shatter'),
    api=('videobuilder.capabilities.sound.impact_hit.impact_hit',
         'videobuilder.capabilities.sound.impact_hit.waveform',
         'videobuilder.impact.shake'),
    demo=film,
)

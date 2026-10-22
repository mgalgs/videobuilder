"""The shared demo kit: every technique's demo is built from these, so the set
reads as one family -- the same 16:9 frame, background, palette and length,
and the same plain subjects (a card, a dot, a word, a photo) to animate.

    from .. import _demo as demo

    def draw(n, cv):
        p = demo.phase(n, 0.5, 1.5)          # 0 -> 1 between 0.5 s and 1.5 s
        demo.card(cv, demo.W / 2, demo.H / 2 + 200 * (1 - p))

    TECHNIQUE = Technique(..., demo=lambda: demo.film(draw))

A transition is a function `transition(cv, a, b, p)`: `a` and `b` draw the
outgoing and incoming scenes (each `a(cv)`), `p` runs 0 -> 1 across the
transition. `two_scenes(transition)` demos one between `scene_a` and
`scene_b`; a real film calls the same function inside its own overlap.

Styling comes from `videobuilder/compendium/kit.py`. Extend this kit only
through a technique's own module (or a `_helper.py` beside it).
"""
import math

import videobuilder as vb

from ..compendium import kit

BG, INK, MUTED, ACCENT, TEAL, LINE = kit.BG, kit.INK, kit.MUTED, kit.ACCENT, kit.TEAL, kit.LINE
FORMAT = kit.F16
W, H = FORMAT.width, FORMAT.height
FPS = 30
SECONDS = 3.0

font = kit.font
mono = kit.mono


def film(draw, seconds=SECONDS, **kw):
    """A demo `vb.Film`: `draw(n, cv)` over `seconds` at 30 fps, 16:9, on the
    kit's background. `kw` passes through (`sounds=`, `audio=` for sound
    techniques)."""
    return vb.Film(draw=draw, fps=FPS, frames=round(seconds * FPS), formats=(FORMAT,), background=BG, **kw)


def phase(n, start, end):
    """Progress 0 -> 1 of frame `n` between `start` and `end` seconds, clamped."""
    return vb.clamp01((n / FPS - start) / (end - start))


def floor(cv, y, color=MUTED):
    """A ground line across the frame at `y`, for things that land."""
    cv.line(80, y, W - 80, y, color, width=3)


def dot(cv, cx, cy, r=34, color=ACCENT, alpha=1.0):
    """A filled circle centred at (cx, cy)."""
    cv.sector(cx, cy, r, 0, 2 * math.pi, color, alpha=alpha)


def card(cv, cx, cy, w=260, h=160, color=ACCENT, alpha=1.0, scale=1.0):
    """A plain UI-ish card centred at (cx, cy): a rounded panel with a soft
    shadow and two bars standing in for text. `scale` grows it about its centre."""
    w, h = w * scale, h * scale
    x, y = cx - w / 2, cy - h / 2
    with cv.layer(opacity=alpha):
        cv.shadow(x, y, w, h, radius=18 * scale, dy=10 * scale, blur=28 * scale, color=(0, 0, 0, 0.45))
        cv.rect(x, y, w, h, color, radius=18 * scale)
        bar = h * 0.12
        cv.rect(x + w * 0.12, y + h * 0.3, w * 0.62, bar, INK, radius=bar / 2, alpha=0.95)
        cv.rect(x + w * 0.12, y + h * 0.3 + bar * 2, w * 0.4, bar, INK, radius=bar / 2, alpha=0.6)
    cv.mark('card', x, y, w, h)


def word(cv, text, cx, cy, size=96, color=INK, weight=800, font=None, alpha=1.0):
    """`text` on one line, centred at (cx, cy). Returns its Box."""
    f = font or kit.font(size, weight)
    w, h = vb.text.block_size([text], f)
    return vb.text.draw(cv, [text], f, cx - w / 2, cy - h / 2, color, alpha=alpha)


def photo():
    """A photo-like image (generated in code, so nothing binary ships)."""
    return kit.sample_photo()


def scene_a(cv):
    """The outgoing scene of a transition demo: a full-frame photo, labelled A."""
    img = photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    _label(cv, 'A')


def scene_b(cv):
    """The incoming scene of a transition demo: a light plane with a card, labelled B."""
    cv.fill('#e9e6df')
    card(cv, W / 2, H / 2, w=360, h=220, color=TEAL)
    _label(cv, 'B', ink=BG)


def _label(cv, letter, ink=INK):
    f = kit.font(28, 800)
    vb.text.draw(cv, [f'Scene {letter}'], f, 40, 32, ink)


def two_scenes(transition, seconds=SECONDS, start=0.8, length=1.4, a=scene_a, b=scene_b):
    """A transition demo: `a` holds, `transition(cv, a, b, p)` runs from
    `start` for `length` seconds, then `b` holds."""
    def draw(n, cv):
        p = phase(n, start, start + length)
        if p <= 0:
            a(cv)
        elif p >= 1:
            b(cv)
        else:
            transition(cv, a, b, p)
    return film(draw, seconds)

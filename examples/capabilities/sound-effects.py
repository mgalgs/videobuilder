"""Capability: sound effects. A chip whips in with a whoosh, a button takes a
tap with a click, a notification lands with a ding and a word slams down
with a hit, each sound put on its frame with `vb.sfx.sound(id, at=frame)`
(its peak on the frame); the strip along the bottom marks the four frames
and the playhead crossing them.

    python -m videobuilder sfx fetch            # once: the sound-effects pack
    python -m videobuilder preview examples/capabilities/sound-effects.py

The sounds come from the pack (earshot's bank); tests read the fixture pack,
which has these four.

LOOP = True by enter/hold/exit: the frame is empty but for the title and the
strip at both ends.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 150                    # 5.0 s
WHOOSH, CLICK, DING, HIT = 16, 48, 78, 104
OUT = 126                      # everything leaves from here
CUES = ((WHOOSH, 'whoosh'), (CLICK, 'click'), (DING, 'ding'), (HIT, 'hit'))

SOUNDS = (
    vb.sfx.sound('whoosh_fast/tight', at=WHOOSH, variant='0.5s', gain_db=-6),
    vb.sfx.sound('fit/click/floss_lid', at=CLICK, gain_db=-4),
    vb.sfx.sound('pro_notify/ding_2045', at=DING, note='G5', gain_db=-10),
    vb.sfx.sound('pro_impact/short', at=HIT, gain_db=-6),
)

TITLE_F = _kit.font(32, 700)
LABEL_F = _kit.font(20, 600)
WORD_F = _kit.font(64, 850)
BUTTON_F = _kit.font(26, 700)


def ease(p):
    return 1 - (1 - min(1.0, max(0.0, p))) ** 4


def prog(n, a, z):
    return min(1.0, max(0.0, (n - a) / (z - a)))


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv)
    _kit.text_marked(cv, 'title', text.wrap('Sound effects', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    gone = ease(prog(n, OUT, OUT + 14))
    with cv.layer(opacity=1 - gone):
        # The chip whips in from the left, fastest as it arrives (the whoosh's peak).
        p = ease(prog(n, WHOOSH - 6, WHOOSH + 6))
        if n >= WHOOSH - 6:
            x = -260 + (s.x + 260) * p
            _kit.rect_marked(cv, 'chip', x, s.y + 80, 230, 96, '#262932', radius=22)
            cv.rect(x + 22, s.y + 108, 40, 40, _kit.ACCENT, radius=12)
            text.draw(cv, ['Whip in'], BUTTON_F, x + 78, s.y + 112, _kit.INK)
        # A button pressed on the click's frame.
        if n >= CLICK - 20:
            pressed = CLICK <= n < CLICK + 4
            sc = 0.94 if pressed else 1.0
            bx, by, bw, bh = s.right - 230, s.y + 80, 230, 96
            with cv.layer(dx=(bx + bw / 2) * (1 - sc), dy=(by + bh / 2) * (1 - sc), scale=sc,
                          opacity=ease(prog(n, CLICK - 20, CLICK - 12))):
                _kit.rect_marked(cv, 'button', bx, by, bw, bh, _kit.TEAL, radius=22)
                text.draw(cv, ['Send'], BUTTON_F, bx, by + 30, '#0d2420', align='center', width=bw)
            age = n - CLICK
            if 0 <= age < 12:
                cv.arc(bx + bw / 2, by + bh / 2, 60 + age * 6, 0, 2 * math.pi, _kit.INK, width=3,
                       alpha=0.5 * (1 - age / 12))
        # A notification drops in, landing on the ding.
        if n >= DING - 8:
            y = s.y + 210 - 120 * (1 - ease(prog(n, DING - 8, DING)))
            _kit.rect_marked(cv, 'note', s.x, y, s.w, 84, '#262932', radius=20)
            cv.rect(s.x + 20, y + 22, 40, 40, _kit.ACCENT, radius=20)
            text.draw(cv, ['Sent: launch-cut.mp4'], BUTTON_F, s.x + 78, y + 26, _kit.INK)
        # The word slams down on the hit, with a short flash.
        if n >= HIT - 4:
            k = ease(prog(n, HIT - 4, HIT))
            sc = 1.6 - 0.6 * k
            cy = s.y + 380
            with cv.layer(dx=s.cx * (1 - sc), dy=cy * (1 - sc), scale=sc, opacity=k):
                box = text.draw(cv, ['LAUNCH'], WORD_F, s.x, cy - 40, _kit.INK, align='center', width=s.w)
            cv.mark('word', *box)
            if HIT <= n < HIT + 6:
                cv.fill(_kit.INK, alpha=0.35 * (1 - (n - HIT) / 6))
    strip(cv, s, n)


def strip(cv, s, n):
    """The film's frames along the bottom: a tick on each sound's frame, the playhead crossing it."""
    y = s.bottom - 40
    cv.line(s.x, y, s.right, y, _kit.LINE, width=3)
    for at, name in CUES:
        x = s.x + s.w * at / TOTAL
        lit = 0 <= n - at < 10
        cv.line(x, y - 14, x, y + 14, _kit.ACCENT if lit else _kit.MUTED, width=3)
        text.draw(cv, [f'{name} f{at}'], LABEL_F, x - 60, y - 46, _kit.INK if lit else _kit.MUTED, align='center',
                  width=120)
    px = s.x + s.w * n / TOTAL
    cv.rect(px - 2, y - 20, 4, 40, _kit.INK)
    cv.mark('strip', s.x, y - 46, s.w, 66)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG, sounds=SOUNDS,
               keyframes=((WHOOSH, 'whoosh'), (CLICK, 'click'), (DING + 6, 'ding'), (HIT + 8, 'hit')))

if __name__ == '__main__':
    vb.main(__file__)

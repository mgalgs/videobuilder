"""Capability: kinetic typography. A short headline wraps with balanced line
breaks, reveals word by word, and the variable-font weight itself animates in
as each word lands -- thin to bold, not just appearing.

    python -m videobuilder preview examples/capabilities/kinetic-typography.py

LOOP = True: the words fade out together (quick, not staggered the way they
arrived), landing on an empty frame that matches frame 0, where no word has
started yet.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30

COPY = 'Words land with weight'
SIZE = 56
START_WEIGHT, FINAL_WEIGHT = 380, 750
WEIGHT_SPAN = 18          # frames for a word's weight to go thin -> bold
RISE = vb.damped(0.75, hz=4.0)   # the little settle as each word lands
STAGGER = 3               # frames between words starting (100 ms at 30 fps)

HOLD_END = 48
FADE_START = 48
FADE_LEN = 12
TOTAL = 70                # 2.33 s

FINAL_FONT = _kit.font(SIZE, FINAL_WEIGHT)
CX, CY = _kit.FORMAT.width / 2, _kit.FORMAT.height / 2
SAFE_W = _kit.FORMAT.width - 2 * 64


def _layout():
    lines = text.wrap(COPY, FINAL_FONT, SAFE_W, balance=True)
    lh = text.line_height(FINAL_FONT)
    _, block_h = text.block_size(lines, FINAL_FONT)
    top = CY - block_h / 2
    space_w = text.measure(' ', FINAL_FONT)
    words = []
    delay = 0
    for i, line in enumerate(lines):
        line_w = text.measure(line, FINAL_FONT)
        x = CX - line_w / 2
        y = top + i * lh
        for w in line.split(' '):
            words.append((w, x, y, delay))
            x += text.measure(w, FINAL_FONT) + space_w
            delay += STAGGER
    return words


WORDS = _layout()


def draw(n, cv):
    cv.fill(_kit.BG)
    fade = vb.interpolate(n, [FADE_START, FADE_START + FADE_LEN], [1, 0], ease=vb.ease_in_expo)
    for i, (word, x, y, delay) in enumerate(WORDS):
        local_f = n - delay
        rise = vb.clamp01(vb.spring_at(local_f, FPS, **RISE))
        a = rise * fade
        if a <= 0.01:
            continue
        weight = round(vb.interpolate(local_f, [0, WEIGHT_SPAN], [START_WEIGHT, FINAL_WEIGHT], ease=vb.ease_out_quint))
        f = _kit.font(SIZE, weight)
        dy = (1 - rise) * 14
        box = text.draw(cv, [word], f, x, y + dy, _kit.INK, alpha=a)
        cv.mark(f'word-{i}', *box)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((10, 'landing'), (40, 'settled')))

if __name__ == '__main__':
    vb.main(__file__)

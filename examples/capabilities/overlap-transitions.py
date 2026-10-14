"""Capability: overlap transitions. Three cuts on a six-beat cycle -- card A
holds, card B slides up over it, then A slides back up over B -- built from
`Segment(overlap=k)`, not a crossfade bolted on afterwards.

    python -m videobuilder preview examples/capabilities/overlap-transitions.py

LOOP = True: the clip starts on card A at rest (segment `a1`, frame 0) and
ends on card A at rest again (segment `a2`'s settled tail), so the loop
point is itself an ordinary cut, not a hidden seam.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
GRID = _kit.grid(bpm=120)                 # 15 frames/beat
OVERLAP_BEATS = 1
TIMELINE = vb.Timeline(GRID, [
    vb.Segment('a1', 0, 2),
    vb.Segment('b', 2, 4, overlap=OVERLAP_BEATS),
    vb.Segment('a2', 4, 6, overlap=OVERLAP_BEATS),
], end=6)                                 # 90 frames, 3.0 s

# The letter/colour on screen is the same for `a1` and `a2` (both are "card
# A"); the two instances are never live at once, so sharing names is safe
# and lets the overlap allowance below cover both.
OVERLAP_OK = {('card-a', 'letter-a'), ('card-b', 'letter-b')}

CARDS = {'a': (_kit.ACCENT, 'A'), 'b': (_kit.TEAL, 'B')}
OVERLAP_FRAMES = GRID.b(OVERLAP_BEATS)    # 15

TITLE_F = _kit.font(32, 700)
LETTER_F = _kit.font(160, 700)


def slide_p(shot):
    """0 (still entering, below the box) .. 1 (fully in place)."""
    if not shot.segment.overlap or shot.f >= OVERLAP_FRAMES:
        return 1.0
    return vb.interpolate(shot.f, [0, OVERLAP_FRAMES], [0, 1], ease=vb.ease_in_out_quart)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Overlap transitions', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    box = s.pad(130, 0, 0, 0)
    with cv.clip(*box):
        for shot in TIMELINE.live(n):
            letter = 'a' if shot.name.startswith('a') else 'b'
            color, glyph = CARDS[letter]
            # the outgoing shot (shot.exit is not None) holds still under the
            # incoming one; only the incoming card moves -- the one hero move.
            y = box.y if shot.exit is not None else box.y + box.h * (1 - slide_p(shot))
            cv.rect(box.x, y, box.w, box.h, _kit.LINE, radius=24)
            cv.outline(box.x, y, box.w, box.h, color, width=4, radius=24)
            cv.mark(f'card-{letter}', box.x, y, box.w, box.h)

            lines = text.wrap(glyph, LETTER_F, box.w)
            _, lh = text.block_size(lines, LETTER_F)
            ly = y + (box.h - lh) / 2
            letter_box = text.draw(cv, lines, LETTER_F, box.x, ly, _kit.INK, align='center', width=box.w)
            cv.mark(f'letter-{letter}', *letter_box)


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((10, 'A holds'), (37, 'B slides over A'), (50, 'B holds'),
                          (67, 'A slides back over B'), (82, 'A holds again')))

if __name__ == '__main__':
    vb.main(__file__)

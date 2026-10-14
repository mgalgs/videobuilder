"""Capability: gauges and rings. A ring gauge sweeps from empty to its
reading as an arc, with the number centred inside it -- the shape for a
single score or percentage, not a comparison.

    python -m videobuilder preview examples/capabilities/gauges-and-rings.py

LOOP = True: the sweep fills in, holds, then sweeps back down to zero (the
reading counts back down with it), resting on the bare track at both ends.
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

TARGET = 0.72          # 72%
LABEL = 'of capacity'

ENTER_LEN = 42
HOLD_END = 78
EXIT_START = HOLD_END
EXIT_LEN = 24
TOTAL = 110            # ~3.67 s

R = 180
WIDTH = 28
START_ANGLE = -math.pi / 2   # 12 o'clock; cv.arc sweeps clockwise from here
CX, CY = _kit.FORMAT.width / 2, _kit.FORMAT.height / 2

NUMBER_F = _kit.font(120, 700, family=_kit.MONO)
LABEL_F = _kit.font(22, 600)

# The sweep is drawn on top of the track, and the reading sits inside both:
# all three marks legitimately share the same circular footprint.
OVERLAP_OK = (('track', 'sweep'), ('track', 'reading'), ('sweep', 'reading'))


def p_at(n):
    """0 -> TARGET -> 0, eased both ways, held in between."""
    if n < ENTER_LEN:
        return vb.interpolate(n, [0, ENTER_LEN], [0, TARGET], ease=vb.ease_out_expo)
    if n < EXIT_START:
        return TARGET
    local = n - EXIT_START
    if local < EXIT_LEN:
        return vb.interpolate(local, [0, EXIT_LEN], [TARGET, 0], ease=vb.ease_in_expo)
    return 0.0


def draw(n, cv):
    cv.fill(_kit.BG)
    hw = WIDTH / 2
    box = (CX - R - hw, CY - R - hw, 2 * (R + hw), 2 * (R + hw))
    cv.arc(CX, CY, R, START_ANGLE, START_ANGLE + 2 * math.pi, _kit.LINE, width=WIDTH)
    cv.mark('track', *box)

    p = p_at(n)
    if p > 0.004:
        cv.arc(CX, CY, R, START_ANGLE, START_ANGLE + p * 2 * math.pi, _kit.ACCENT, width=WIDTH)
        cv.mark('sweep', *box)

        pct = f'{p * 100:.0f}%'
        number_lines = [pct]
        label_lines = text.wrap(LABEL, LABEL_F, 2 * R)
        nw, nh = text.block_size(number_lines, NUMBER_F)
        lw, lh = text.block_size(label_lines, LABEL_F)
        total_h = nh + 10 + lh
        top = CY - total_h / 2
        text.draw(cv, number_lines, NUMBER_F, CX - nw / 2, top, _kit.INK)
        text.draw(cv, label_lines, LABEL_F, CX - lw / 2, top + nh + 10, _kit.MUTED,
                  align='center', width=lw)
        cv.mark('reading', CX - max(nw, lw) / 2, top, max(nw, lw), total_h)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((20, 'sweeping'), (56, 'reading 72%')))

if __name__ == '__main__':
    vb.main(__file__)

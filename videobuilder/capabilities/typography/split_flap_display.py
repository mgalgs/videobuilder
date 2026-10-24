"""Split-flap display: the same idea as Split-flap board (`type_split_flap.py`),
which keeps the capability -- both call `vb.type.draw` with the very Type
style `videobuilder.type.splitflap.STYLE`. This module's own code stays (a
film may still import it), but it is no longer a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'type-split-flap'

# Longer than the demo, so the board clatters in and holds without reaching its exit.
BOARD = vb.type.props(lines=['FLIGHT 207', 'NOW BOARDING'], ink=demo.INK, paper=demo.BG, accent=demo.ACCENT,
                      length=4.5)


def draw(n, cv):
    vb.type.draw(cv, 'split-flap', BOARD, n / demo.FPS - 0.2)

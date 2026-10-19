"""The Type family: two lines of the launch said as named type styles, a
split-flap board and then rubber letters, each running its own enter, hold
and exit inside its cut (vb.type)."""
import videobuilder as vb

from .kit import ACCENT, BG, GRID, INK

FLAP = vb.type.props(lines=['Lumen 2.0', 'Now boarding'], ink=INK, paper=BG, accent=ACCENT)
RUBBER = vb.type.props(lines=['Say it', 'with a bounce'], ink=INK, paper=BG, accent=ACCENT)


def _style(name, p):
    def draw(cv, s, st):
        cv.fill(BG)
        vb.type.draw(cv, name, vb.type.props(p, length=s.length / GRID.fps), s.f / GRID.fps, box=st.content)
    return draw


SCENES = {'type-flap': _style('split-flap', FLAP), 'type-rubber': _style('rubber', RUBBER)}

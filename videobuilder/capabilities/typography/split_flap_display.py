"""Split-flap display: videobuilder already has it as the `split-flap` type
style (`vb.type.draw(cv, 'split-flap', props, t)`), so this entry only names
it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Longer than the demo, so the board clatters in and holds without reaching its exit.
BOARD = vb.type.props(lines=['FLIGHT 207', 'NOW BOARDING'], ink=demo.INK, paper=demo.BG, accent=demo.ACCENT,
                      length=4.5)


def draw(n, cv):
    vb.type.draw(cv, 'split-flap', BOARD, n / demo.FPS - 0.2)


CAPABILITY = Capability(
    id='split-flap-display',
    name='Split-flap display',
    family='typography',
    group='Mechanical display',
    aliases=('split-flap board', 'departures board', 'flap display', 'solari board'),
    definition='Each character sits on a hinged card that flips down through a run of letters, '
               'clattering cell by cell until the whole board settles on the message.',
    phrasings=('make the title flip in like an old airport arrivals board',
               'letters that flap through the alphabet and land on the words',
               'a train station board where the text clicks into place'),
    related=('split-screen-transition', 'split-screen-comparison', 'character-3d-flip', 'flip', 'word-flip-in',
             'tile-flip'),
    api=('videobuilder.type.draw', 'videobuilder.type.splitflap.STYLE'),
    demo=lambda: demo.film(draw),
)

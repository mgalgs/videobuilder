"""Split-flap board: one type style of the Type capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/type-split-
flap.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='type-split-flap',
    name='Split-flap board',
    family='typography',
    group='Type styles',
    aliases=('departures board', 'flap display', 'solari board'),
    definition='A departures board: every letter flips through the alphabet and settles.',
    description=("The lines set on a split-flap board, one cell per letter: each cell's flap falls through "
                 'a run of characters before it lands on its own, the cells starting left to right and row '
                 'by row so the lines clatter in as a wave. Blank cells round the copy flip now and then '
                 'through the hold, a lamp beside each line pulses in the accent, and on the exit every '
                 'letter flips back to blank. A tall frame gets a whole board of blank rows round the '
                 'copy. With sound on, the flaps click.'),
    phrasings=('Make the title a split-flap departures board',
               'Flip the quote in letter by letter like an airport board',
               'Show the times on a flip board, with the clicking',
               'make the title flip in like an old airport arrivals board',
               'letters that flap through the alphabet and land on the words',
               'a train station board where the text clicks into place'),
    api=("vb.type.draw(cv, 'split-flap', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-split-flap.py'),
    source=Source('https://x.com/Mike_Andreuzza/status/2112064951925854535', '@Mike_Andreuzza'),
)

"""Rack focus: one type style of the Type capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/type-rack-focus.py`
(an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='type-rack-focus',
    name='Rack focus',
    family='typography',
    group='Type styles',
    definition='Lines pull out of a soft haze into focus, one after another.',
    description=('The lines come out of a soft haze one after another, each pulling into sharp focus as '
                 'the one before blurs back, the way a lens racks between two depths, with soft discs of '
                 'out-of-focus light drifting behind and an accent rule gliding to whichever line is '
                 'sharp. Through the hold the focus keeps racking from line to line; on the exit '
                 'everything goes back into the haze.'),
    phrasings=('Bring the lines into focus one at a time',
               'Make it feel cinematic, the text racking focus',
               'Have the quote drift out of a blur, line by line'),
    api=("vb.type.draw(cv, 'rack-focus', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-rack-focus.py'),
    source=Source('https://x.com/Mike_Andreuzza/status/2112064951925854535', '@Mike_Andreuzza'),
)

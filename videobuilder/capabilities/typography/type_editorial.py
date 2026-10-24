"""Editorial stack: one type style of the Type capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/type-
editorial.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='type-editorial',
    name='Editorial stack',
    family='typography',
    group='Type styles',
    definition='Stacked capitals revealed by hard wipes in the accent, magazine style.',
    description=('A magazine-cover headline: heavy capitals stacked tight and set as big as the frame '
                 'allows, each line revealed by a hard block of the accent that sweeps across it and peels '
                 'away, staggered, under a hairline rule, beside a halftone plate in the accent that fills '
                 "the room the type leaves. Through the hold the plate's dots drift and the lines slide "
                 'against each other; on the exit the blocks sweep back and carry the lines off. Built on '
                 "the compendium's editorial wipe title."),
    phrasings=('Make the headline a magazine cover, big stacked type',
               'Wipe each line on with a block of colour',
               'Give the title an editorial, print look'),
    api=("vb.type.draw(cv, 'editorial', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-editorial.py'),
)

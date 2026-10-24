"""Ukiyo-e woodblock: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-
woodblock.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='look-woodblock',
    name='Ukiyo-e woodblock',
    family='vfx',
    group='Scene looks',
    definition='Flat colour, thick ink lines, and a great wave that curls.',
    description=('A woodblock print: flat fills with thick ink outlines on a paper ground, a graded sky, a '
                 'red sun and sliding cloud strips. A great wave rises out of the open water and curls '
                 'over once each time the look comes on, its foam claws flicking, while slanting rain '
                 'falls.'),
    phrasings=('Make it look like an old Japanese woodblock print',
               'Add a big curling wave, woodblock style',
               'Flat colours and thick black outlines, like a print'),
    api=("looks.paint(cv, 'woodblock', scene, t)",
         'the wave curls on age: pass the seconds since the look came on'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-woodblock.py'),
)

"""Pointillism: one look of the Looks capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/look-pointillism.py`
(an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-pointillism',
    name='Pointillism',
    family='vfx',
    group='Scene looks',
    definition='Ten thousand dots of colour that shimmer.',
    description=('The whole picture built from small round dots, each coloured by the shape it falls in '
                 'and each shimmering towards a neighbouring tone; bands of light roll through the water '
                 'and buildings are banded in warm dots.'),
    phrasings=('Paint it all in tiny dots',
               'Give it a dotty, shimmering painted look',
               'Make it look like a dot painting'),
    api=("looks.paint(cv, 'pointillism', scene, t)",
         'scene.role_at(x, y) colours each dot by its region'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-pointillism.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

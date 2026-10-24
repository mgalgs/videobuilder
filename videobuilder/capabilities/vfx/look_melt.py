"""Surrealist melt: one look of the Looks capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/look-melt.py` (an
`Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-melt',
    name='Surrealist melt',
    family='vfx',
    group='Scene looks',
    definition='A dream: the clock melts, the tower sways like wax.',
    description=('Smooth gradients in a dream light. Buildings and figures sway and sag like warm wax, the '
                 'sun sags and drips into a mirror sea, stones float across the sky, and a clock draped '
                 'over the edge of the land melts and drips from its lowest point.'),
    phrasings=('Make it surreal, like a dream where things melt',
               'Have the clock melt over the edge',
               'Make the buildings sway like they are made of wax'),
    api=("looks.paint(cv, 'melt', scene, t)",
         'scene.ledge() is where the clock drapes: give the scene some land'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-melt.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

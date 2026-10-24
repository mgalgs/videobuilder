"""Bauhaus geometry: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-
bauhaus.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-bauhaus',
    name='Bauhaus geometry',
    family='vfx',
    group='Scene looks',
    definition='Primary colours and simple shapes that turn on the beat.',
    description=('Everything reduced to primary colours, circles, half-discs and blocks on cream: the '
                 "sun's four quarters turn, rows of half-discs roll opposite ways across the water, stars "
                 'become squares and dots that pulse on the beat, and buildings stack up as coloured '
                 'blocks.'),
    phrasings=('Make it geometric, all circles and primary colours',
               'Give it a clean modernist poster look',
               'Have the shapes pulse on the beat'),
    api=("looks.paint(cv, 'bauhaus', scene, t)",
         'Scene(bpm=...) sets the beat the shapes pulse on'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-bauhaus.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

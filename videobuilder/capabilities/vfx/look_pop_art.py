"""Pop-art halftone: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-pop-
art.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-pop-art',
    name='Pop-art halftone',
    family='vfx',
    group='Scene looks',
    definition='Loud flat colour, comic dots, and a burst that pops.',
    description=('Flat loud colours with comic-print dot fills and heavy black outlines: the dots drift, a '
                 'ray burst turns behind everything, white wave lines roll, and a starburst springs in '
                 'every two beats with a short word in it when you give one.'),
    phrasings=('Make it pop art, comic-book dots and bold colours',
               'Put a big POW burst in it on the beat',
               'Give it heavy black outlines and dot shading'),
    api=("looks.paint(cv, 'pop-art', scene, t)",
         "looks.paint(cv, 'pop-art', scene, t, sfx='POW!', font=vb.Font(...))  # the burst's word"),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-pop-art.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

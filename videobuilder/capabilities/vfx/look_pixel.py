"""8-bit pixel: one look of the Looks capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/look-pixel.py` (an
`Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='look-pixel',
    name='8-bit pixel',
    family='vfx',
    group='Scene looks',
    definition='Blocky pixels, everything moving in little steps.',
    description=('The whole scene drawn at a fraction of the resolution and scaled back up hard-edged, '
                 "every move stepped at 8 frames a second like an old game: the water's rows shift a block "
                 'at a time, stars blink with little crosses, lights flash and the beams turn in steps.'),
    phrasings=('Make it look like an old 8-bit video game',
               'Turn the whole scene into chunky pixels',
               'Make the motion choppy, like a retro game'),
    api=("looks.paint(cv, 'pixel', scene, t)",
         "looks.paint(cv, 'pixel', scene, t, block=16)  # bigger pixels"),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-pixel.py'),
)

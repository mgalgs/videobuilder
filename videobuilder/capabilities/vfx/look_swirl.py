"""Post-Impressionist swirl: one look of the Looks capability, built from videobuilder's own API, so
this record only names it and demos it with its worked example film, `examples/capabilities/look-
swirl.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-swirl',
    name='Post-Impressionist swirl',
    family='vfx',
    group='Scene looks',
    definition='Thick dabs of paint; the sky turns in eddies.',
    description=("Every shape laid in with short, loaded, round-capped strokes. The sky's dabs orbit two "
                 'eddies, the inner rings turning faster; halo rings turn round the sun or moon, stars '
                 "spin crowns of dabs, and the water's dabs ride a rolling wave field."),
    phrasings=('Make it look like a swirling oil painting',
               'Paint the sky in thick turning brushstrokes',
               'Give it that starry, swirling night-sky look'),
    api=("looks.paint(cv, 'swirl', scene, t)",
         'the sky eddies sit beside the sun: give the scene a sun to turn them round'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-swirl.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

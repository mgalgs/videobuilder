"""Outline morph: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/outline-morph.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Members, Source

CAPABILITY = Capability(
    id='outline-morph',
    name='Outline morph',
    family='shapes',
    group='Shape morphing',
    category='Motion',
    order=13,
    aliases=('morph', 'shape tween', 'path morph', 'shape interpolation'),
    definition='One outline smoothly becomes the next, not a cut.',
    description=('A circle turns into a document icon and back, its outline resampled to match point for '
                 'point and interpolated with a smooth ease while its colour travels along -- one idea '
                 'turning into the next instead of a hard cut between two shapes.'),
    phrasings=("Don't cut between these icons, morph one into the other",
               'Turn the circle into the document shape smoothly',
               'Let the colour shift as the shape changes, not just the outline',
               'turn the circle into a star smoothly instead of swapping them',
               'have one shape melt into the next',
               'blend this icon into that one without a cut'),
    api=('videobuilder.paths.morph(a, b, t, closed=True)',
         'videobuilder.paths.draw(cv, points, colour, fill=True)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/outline-morph.py'),
    members=Members(ids=('icon-state-morph', 'blob-to-icon-morph')),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)

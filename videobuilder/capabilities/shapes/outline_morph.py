"""Outline morph: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/outline-morph.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='outline-morph',
    name='Outline morph',
    family='shapes',
    group='Shape morphing',
    category='Motion',
    order=13,
    definition='One outline smoothly becomes the next, not a cut.',
    description=('A circle turns into a document icon and back, its outline resampled to match point for '
                 'point and interpolated with a smooth ease while its colour travels along -- one idea '
                 'turning into the next instead of a hard cut between two shapes.'),
    phrasings=("Don't cut between these icons, morph one into the other",
               'Turn the circle into the document shape smoothly',
               'Let the colour shift as the shape changes, not just the outline'),
    api=('videobuilder.paths.morph(a, b, t, closed=True)',
         'videobuilder.paths.draw(cv, points, colour, fill=True)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/outline-morph.py'),
)

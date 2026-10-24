"""Bar charts: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/bar-charts.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='bar-charts',
    name='Bar charts',
    family='broadcast',
    group='Charts',
    category='Type and data',
    order=5,
    definition='Bars grow on the beat, each with a direct label.',
    description=('A bar chart grows its bars on their own beats, with the value labelled directly at the '
                 'end of each bar (not a legend) so it reads correctly even without colour.'),
    phrasings=('Chart these as bars growing on the beat, direct labels',
               'No legend — label each bar directly',
               'Grow the hero bar last so it lands on the verdict'),
    api=('cv.rect(..., radius=..., alpha=...)',
         'vb.spring_at for bar growth',
         'text.draw for direct labels'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/bar-charts.py'),
)

"""Gauges and rings: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/gauges-and-rings.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='gauges-and-rings',
    name='Gauges and rings',
    family='broadcast',
    group='Charts',
    category='Type and data',
    order=6,
    definition='An arc fills to a reading, with a readout in the centre.',
    description=('A ring gauge sweeps from empty to its reading as an arc, with the number centred inside '
                 'it — the shape for a single score, percentage or level rather than a comparison.'),
    phrasings=('Show this as a ring gauge filling to 72%',
               'Use an arc readout, not a bar, for a single score',
               'Sweep the gauge in on the beat'),
    api=('cv.arc(cx, cy, r, a0, a1, colour, width=...)',
         'cv.sector(...)',
         'vb.spring_at drives the sweep angle'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/gauges-and-rings.py'),
)

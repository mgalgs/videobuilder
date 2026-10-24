"""Blueprint filter: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-filter-
blueprint.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='look-filter-blueprint',
    name='Blueprint filter',
    family='vfx',
    group='Filter looks',
    definition='Any picture as chalk lines on a blue grid, a scan line sweeping.',
    description=('Keeps only the edges of whatever the video draws, as chalk lines on a blue sheet ruled '
                 'with a grid. The lines draw in from the top behind a bright scan line when the filter '
                 'comes on; after that the scan line keeps sweeping, a light band shimmers across the grid '
                 'and the chalk boils.'),
    phrasings=('Turn the product screenshots into a blueprint',
               'Show the app as white lines on blue paper',
               'Make the footage look like a technical drawing being scanned'),
    api=("with looks.filter(cv, 'blueprint', t): draw_as_usual(n, cv)",),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-filter-blueprint.py'),
)

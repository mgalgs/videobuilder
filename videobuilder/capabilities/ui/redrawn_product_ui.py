"""Redrawn product UI: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/redrawn-product-ui.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='redrawn-product-ui',
    name='Redrawn product UI',
    family='ui',
    group='Cards & media',
    category='Imagery and camera',
    order=2,
    definition='A crisp vector screen, redrawn from measured blocks.',
    description=('A product screen redrawn as vector shapes and real text instead of a captured bitmap: '
                 'crisp at any size, built from measured blocks stacked edge to edge.'),
    phrasings=('Redraw this screen instead of using a screenshot',
               'Rebuild the settings panel as crisp vector UI',
               "Keep this sharp at every size — redraw it, don't capture it"),
    api=('Box.stack(heights, gap=..., align="top")',
         'cv.rect / cv.outline / text.draw for each block'),
    doc='skill/make-a-video/reference/redrawn-ui.md',
    demo=Example('examples/capabilities/redrawn-product-ui.py'),
)

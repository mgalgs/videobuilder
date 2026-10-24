"""Blueprint: one look of the Looks capability, built from videobuilder's own API, so this record only
names it and demos it with its worked example film, `examples/capabilities/look-blueprint.py` (an
`Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='look-blueprint',
    name='Blueprint',
    family='vfx',
    group='Scene looks',
    definition='Chalk lines that draw the scene in on a blue grid.',
    description=("A technical drawing: the scene's outlines draw themselves in one after another in chalk "
                 'on a sliding blue grid, then dashed beams sweep, swell lines roll across the water, a '
                 'dimension line measures the tallest building and a compass rose turns in the corner.'),
    phrasings=('Make it look like a blueprint that draws itself',
               'Show it as a technical drawing in white lines',
               'Draw the scene in chalk on blue paper'),
    api=("looks.paint(cv, 'blueprint', scene, t)",
         "looks.paint(cv, 'blueprint', scene, t, age, font=vb.Font(...))  # labels on the dimension line"),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-blueprint.py'),
)

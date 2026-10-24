"""Letter cloud: one type style of the Type capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/type-letter-
cloud.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='type-letter-cloud',
    name='Letter cloud',
    family='typography',
    group='Type styles',
    definition='Letters scattered in 3D fly together into the words.',
    description=('The letters start scattered through 3D space -- near and far, turned every way, tinted '
                 'by the accent the deeper they sit -- and fly together on springs into the words while '
                 "the camera swings round to face them (the extruded 3D title's camera). Through the hold "
                 'the camera keeps drifting, with small letters drifting through the depth behind; on the '
                 'exit the letters burst past the camera.'),
    phrasings=('Have the letters fly together out of a 3D cloud',
               'Scatter the title in space and assemble it',
               'Make the words come together from flying letters'),
    api=("vb.type.draw(cv, 'letter-cloud', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-letter-cloud.py'),
    source=Source('https://x.com/Mike_Andreuzza/status/2112064951925854535', '@Mike_Andreuzza'),
)

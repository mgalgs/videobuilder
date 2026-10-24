"""Kinetic typography: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/kinetic-typography.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='kinetic-typography',
    name='Kinetic typography',
    family='typography',
    group='Variable font',
    category='Type and data',
    order=1,
    definition='Balanced wrapping, word-by-word reveal, live weight.',
    description=('A headline wraps with balanced line breaks, reveals word by word, and its variable-font '
                 'weight itself animates in — all real text layout, not an image of text.'),
    phrasings=('Reveal this headline word by word, with neatly balanced line breaks',
               'Animate the weight in as it lands, thin to bold',
               'Make the type itself the motion here'),
    api=('text.wrap(copy, font, width, balance=True)',
         'vb.Font(..., weight=interpolated)',
         'text.draw'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/kinetic-typography.py'),
)

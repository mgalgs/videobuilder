"""Generated art: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/generated-art.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='generated-art',
    name='Generated art',
    family='particles',
    group='Tiling & patterns',
    category='Imagery and camera',
    order=4,
    definition='Cairo paths and gradients, seeded so they repeat.',
    description=('A procedural pattern drawn straight from cairo paths and a gradient, from a seeded '
                 'random source so the same look renders the same way every time — no stock art, no '
                 'network.'),
    phrasings=('Generate a background pattern, not a stock image',
               'Use a generated pattern that renders exactly the same every time',
               'Draw this as paths and a gradient, not a bitmap'),
    api=('cv.ctx  # raw cairo Context',
         'cairo.LinearGradient / RadialGradient',
         'random.Random(seed)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/generated-art.py'),
)

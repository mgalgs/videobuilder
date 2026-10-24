"""Every format, recomposed: built from videobuilder's own API, so this record only names it and demos
it with its worked example film, `examples/capabilities/every-format.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='every-format',
    name='Every format, recomposed',
    family='ui',
    group='Layout & lists',
    category='Timing, sound and formats',
    order=5,
    definition='One scene, laid out separately for three shapes.',
    description=('The same scene laid out three separate ways — 9:16, 16:9 and 1:1 — each from its own '
                 'per-format layout table, not one layout cropped three ways.'),
    phrasings=('Lay this out for 9:16, 16:9 and 1:1, not just one format',
               'Recompose this for square, not just crop it',
               'Give portrait its own layout table, not a cropped landscape one'),
    api=('per_format(LAYOUTS, cv)',
         "one LAYOUTS entry per vb.Format, each computed from that format's own geometry"),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/every-format.py'),
)

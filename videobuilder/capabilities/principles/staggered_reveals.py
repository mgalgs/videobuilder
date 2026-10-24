"""Staggered reveals: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/staggered-reveals.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='staggered-reveals',
    name='Staggered reveals',
    family='principles',
    group='Stagger',
    category='Motion',
    order=3,
    definition='A list that cascades in, one item after the next.',
    description=('List chips reveal in sequence, each starting while the one before it is still '
                 'mid-flight, instead of all arriving at once — the cascade that makes a list of features '
                 'or steps read as a group.'),
    phrasings=('Stagger these in as a list, cascading',
               "Don't pop them all in at once; stagger it",
               'Reveal the words one at a time, staggered'),
    api=('vb.spring_at(f - delay, fps, **vb.damped(...))',
         'per-item frame delay (40-80ms list items)'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/staggered-reveals.py'),
    source=Source('https://x.com/flxrnc/status/2105311836190978392', '@flxrnc'),
)

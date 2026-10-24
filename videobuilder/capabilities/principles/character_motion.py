"""Character motion: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/character-motion.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='character-motion',
    name='Character motion',
    family='principles',
    group='Classic principles',
    category='Motion',
    order=5,
    definition='Anticipation, squash and stretch, and follow-through.',
    description=('A hopping shape anticipates before it leaps (a crouch), stretches in the air, squashes '
                 'on landing, and settles with a little follow-through — the full vocabulary from the '
                 "animator's handbook, timed in frames."),
    phrasings=('Give this hop some anticipation and squash and stretch',
               'Make the landing squash, then settle with follow-through',
               'This motion feels flat; add some character to it'),
    api=('vb.interpolate',
         'vb.spring_at(f, fps, **vb.damped(0.22, hz=2.2))  # follow-through',
         'frame-level timing in reference/motion.md'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/character-motion.py'),
    poster=42,  # squashed, landing, not round
    source=Source('https://x.com/flxrnc/status/2105311836190978392', '@flxrnc'),
)

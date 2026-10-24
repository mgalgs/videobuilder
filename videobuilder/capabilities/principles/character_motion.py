"""Character motion: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/character-motion.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example, Members, Source

CAPABILITY = Capability(
    id='character-motion',
    name='Character motion',
    family='principles',
    group='Classic principles',
    category='Motion',
    order=5,
    aliases=('hopping loop', 'jump cycle'),
    definition='Anticipation, squash and stretch, and follow-through.',
    description=('A hopping shape anticipates before it leaps (a crouch), stretches in the air, squashes '
                 'on landing, and settles with a little follow-through — the full vocabulary from the '
                 "animator's handbook, timed in frames."),
    phrasings=('Give this hop some anticipation and squash and stretch',
               'Make the landing squash, then settle with follow-through',
               'This motion feels flat; add some character to it'),
    api=('vb.interpolate',
         'vb.spring_at(f, fps, **vb.damped(0.22, hz=2.2))  # follow-through',
         'frame-level timing in reference/motion.md',
         'videobuilder.capabilities.principles.anticipation.anticipate(x)',
         'videobuilder.capabilities.principles.squash_and_stretch.squash_stretch(cv, ax, ay, amount)',
         'videobuilder.capabilities.principles.follow_through.follow_through(path, t)',
         'videobuilder.capabilities.principles.hop_cycle.hop_cycle(u)'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/character-motion.py'),
    poster=42,  # squashed, landing, not round
    members=Members(ids=('anticipation', 'squash-and-stretch', 'follow-through'), noun=('principle', 'principles')),
    source=Source('https://x.com/flxrnc/status/2105311836190978392', '@flxrnc'),
)

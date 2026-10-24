"""Rubber letters: one type style of the Type capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/type-
rubber.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='type-rubber',
    name='Rubber letters',
    family='typography',
    group='Type styles',
    definition='Bouncy letters that squash, stretch and settle on springs.',
    description=('Each letter drops onto its line and its spring carries it on: where the spring '
                 'overshoots, the letter squashes flat and wide against the line; where it swings back, it '
                 'stretches up tall; then it settles, a soft shadow in the accent spreading under it. '
                 'Through the hold a hop runs along each line now and then, every letter jumping in turn; '
                 'on the exit they squash down and pop away. With sound on, each landing is a soft pop.'),
    phrasings=('Make the slogan bounce in, letters on springs',
               'Give the title a squishy, jelly bounce',
               'Have the letters drop in and wobble'),
    api=("vb.type.draw(cv, 'rubber', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-rubber.py'),
)

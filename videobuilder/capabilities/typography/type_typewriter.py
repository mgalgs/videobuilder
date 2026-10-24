"""Typewriter: one type style of the Type capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/type-typewriter.py`
(an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='type-typewriter',
    name='Typewriter',
    family='typography',
    group='Type styles',
    aliases=('typing effect', 'type-on text', 'typed line'),
    definition='Letters strike in one at a time, a little uneven, the caret riding the line.',
    description=('The lines typed onto the paper one key at a time with a human, uneven cadence: each '
                 'letter lands a touch off its line and a touch light or heavy, the way a typebar strikes, '
                 'beside a margin rule in the accent, with a caret riding the end of the line. Through the '
                 'hold the caret blinks and the sheet drifts in; on the exit the sheet feeds up and away. '
                 'With sound on, every letter is a key strike and the bell rings when the last line is in.'),
    phrasings=('Type the quote out like an old typewriter',
               'Have the title type itself on, letter by letter',
               'Make it look typed, with the key sounds'),
    api=("vb.type.draw(cv, 'typewriter', props, t)",
         'videobuilder.capabilities.typography.typewriter_reveal.draw_typed(cv, text, font, x, y, p, color)'
         '  # plain one-line typing, any font',
         'videobuilder.capabilities.typography.typewriter_reveal.typed(text, p)'),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-typewriter.py'),
)

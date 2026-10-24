"""Terminal: one type style of the Type capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/type-terminal.py`
(an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='type-terminal',
    name='Terminal',
    family='typography',
    group='Type styles',
    definition='Typed at a prompt with a block cursor, then deleted back to the prompt.',
    description=('The lines typed in at a terminal prompt (an accent `>` before each), with a block cursor '
                 'riding the end of the line, under faint, still scanlines. Through the hold the cursor '
                 'blinks and the screen pushes in; on the exit every line is deleted back to the prompt. '
                 "Built on the compendium's terminal title: the same human keystroke cadence. With sound "
                 'on, every letter is a key tick.'),
    phrasings=('Type the headline in like a terminal command',
               'Make it look like code being typed at a prompt',
               'Put the title on a command line with a blinking cursor'),
    api=("vb.type.draw(cv, 'terminal', props, t)",),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type-terminal.py'),
)

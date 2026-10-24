"""Terminal log: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/terminal-log.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='terminal-log',
    name='Terminal log',
    family='typography',
    group='Typewriter and terminal',
    category='Type and data',
    order=3,
    definition='A terminal or chat log that types, prints and scrolls.',
    description=('A running log in a window, like an agent at work in a terminal: its thinking in one '
                 'style, its commands typed at a prompt key by key with an uneven human rhythm, their '
                 'output appearing whole in another colour. Long lines wrap; once the window is full it '
                 'eases up a line at a time and old lines leave at the top. Every keystroke can click and '
                 'every printed line tick, hundreds of sounds if the session is long.'),
    phrasings=("Show the agent's session as a terminal, typing and scrolling",
               'Put its thinking in grey italics and the commands in white after a prompt',
               'Let the output scroll up as new lines arrive',
               'Add a key click for every letter typed'),
    api=("vb.terminal.Kind(vb.Font(mono, 28, style='italic'), colour, prefix='$ ', typed=True)",
         'events = vb.terminal.paced([(kind, text), ...], KINDS)  # or (t, kind, text) by hand',
         'LOG = vb.TerminalLog(events, KINDS); LOG.draw(cv, t, box)',
         'Film(sounds=LOG.sounds(at=0, fps=FPS))'),
    doc='skill/make-a-video/reference/terminal.md',
    demo=Example('examples/capabilities/terminal-log.py'),
    poster=124,
)

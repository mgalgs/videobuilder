"""Woodblock filter: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-filter-
woodblock.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='look-filter-woodblock',
    name='Woodblock filter',
    family='vfx',
    group='Filter looks',
    aliases=('woodcut', 'block print', 'relief print'),
    definition='Any picture as a woodblock print, its paper boiling on twos.',
    description=('Restyles whatever the video draws into a few flat inks -- indigo, Prussian blue, '
                 'vermilion, ochre, sage -- on cream paper, every strong edge inked in a thick line. The '
                 'paper grain and the ink lines boil on twos, a new impression every fifteenth of a '
                 'second, so a held photo breathes.'),
    phrasings=('Make this photo look like an old Japanese woodblock print',
               'Flat colours and thick ink lines on paper, for the whole video',
               'Make the screen recording look hand-printed'),
    api=("with looks.filter(cv, 'woodblock', t): draw_as_usual(n, cv)",
         'videobuilder.capabilities.vfx.linocut.linocut(cv, t)  # the LINOCUT treat helper',
         'videobuilder.capabilities.vfx.linocut.treat(im, t, age, u)'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-filter-woodblock.py'),
)

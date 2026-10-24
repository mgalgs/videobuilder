"""Pointillism filter: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-filter-
pointillism.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-filter-pointillism',
    name='Pointillism filter',
    family='vfx',
    group='Filter looks',
    definition='Any picture rebuilt from shimmering dots of its own colours.',
    description=('Rebuilds whatever the video draws from thousands of seeded dots, each taking the colour '
                 'under it nudged warmer or cooler, on a pale ground. Every dot circles a little and '
                 'shimmers, so the whole surface swims even on a still photo.'),
    phrasings=('Paint this photo in tiny dots',
               'Make the whole video look like a dot painting',
               'Give the footage a shimmering, painted-in-dots look'),
    api=("with looks.filter(cv, 'pointillism', t): draw_as_usual(n, cv)",),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-filter-pointillism.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755', '@Voxyz_ai'),
)

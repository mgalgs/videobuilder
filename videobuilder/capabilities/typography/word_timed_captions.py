"""Word-timed captions: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/word-timed-captions.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='word-timed-captions',
    name='Word-timed captions',
    family='typography',
    group='Lyrics and captions',
    category='Type and data',
    order=2,
    definition='Captions that follow the words as they are spoken.',
    description=("A speaker's words run along the bottom of the clip one short line at a time, each line "
                 'measured to fit the frame: the word being spoken lights up in yellow as it is said, and '
                 'a chosen keyword stays green, so the captions keep pace with the voice instead of '
                 'sitting there as a block of text.'),
    phrasings=('Add captions that follow along word by word',
               'Highlight each word in yellow as it is said',
               'Make the word "mornings" stand out in green in the captions'),
    api=('vb.captions.parse(text) / vb.captions.load(path)  # .vtt or .srt, word times kept',
         'track.slice(a, b).shift(at - a)  # a clip cut from a longer source',
         'vb.captions.draw(cv, track, t, keywords={...}, font=..., safe=...)'),
    doc='skill/make-a-video/reference/captions.md',
    demo=Example('examples/capabilities/word-timed-captions.py'),
    source=Source('https://www.youtube.com/watch?v=JOSJE6hQbdE', 'The Anomaly Archive'),
)

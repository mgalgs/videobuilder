"""Overlap transitions: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/overlap-transitions.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='overlap-transitions',
    name='Overlap transitions',
    family='transitions',
    group='Cuts',
    category='Motion',
    order=11,
    definition='One segment slides over the outgoing one — no hard cut.',
    description=('Instead of a hard cut, the next scene starts on its own beat while the one before it '
                 'keeps drawing underneath for a few more frames: a transition built into the timeline '
                 'itself, not a crossfade bolted on.'),
    phrasings=('Transition between these, not a hard cut',
               'Slide the end card in over the previous scene, overlapping for a beat',
               'Keep the previous scene visible while the next one arrives'),
    api=('vb.Segment(..., overlap=k)',
         'Timeline.live(n) -> Shots back to front',
         'Shot.exit'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/overlap-transitions.py'),
)

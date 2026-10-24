"""Seamless loops: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/seamless-loops.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='seamless-loops',
    name='Seamless loops',
    family='principles',
    group='Cycles & loops',
    category='Timing, sound and formats',
    order=6,
    definition='A clip built to play forever with no visible seam.',
    description=('A continuously looping shot, its motion driven by a repeating cycle, so the state at the '
                 'last frame and the state at frame 0 are mathematically the same point in the cycle, not '
                 'just visually close.'),
    phrasings=('Make this loop seamlessly',
               'This needs to play on repeat with no jump at the seam',
               'Drive the motion in a cycle that wraps around cleanly, with no jump at the seam'),
    api=('phase = (n % length) / length',
         'vb.linear for phase/rotation',
         'LOOP = True  # tells check.py to grade the seam'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/seamless-loops.py'),
)

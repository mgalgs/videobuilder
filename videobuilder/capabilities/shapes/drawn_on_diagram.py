"""Drawn-on diagram: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/drawn-on-diagram.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='drawn-on-diagram',
    name='Drawn-on diagram',
    family='shapes',
    group='Hand-drawn & traditional',
    category='Motion',
    order=12,
    definition='A whiteboard diagram drawn stroke by stroke, pen tracked by camera.',
    description=('A small whiteboard diagram -- boxes, arrows, an icon, handwritten-looking labels -- '
                 'draws on stroke by stroke with a little hand jitter, the camera tracking the pen across '
                 'a board bigger than the frame, ending in a pull-back that shows the whole board at once.'),
    phrasings=('Draw this diagram on stroke by stroke, like a whiteboard',
               'Track the camera on the pen as it draws, then pull back',
               'Give the lines a bit of hand-drawn wobble, not perfectly straight'),
    api=('videobuilder.paths.reveal(points, fraction)',
         'videobuilder.paths.jitter(points, seed)',
         'cv.layer(dx=.., dy=.., scale=..)  # the tracking camera'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/drawn-on-diagram.py'),
)

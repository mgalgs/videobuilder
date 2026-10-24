"""Hard-light sweep: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/hard-light-sweep.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='hard-light-sweep',
    name='Hard-light sweep',
    family='camera',
    group='Lighting & surface',
    category='Imagery and camera',
    order=6,
    definition='A hard-edged band of light sweeps across the shot.',
    description=('A dim, shadowed version of the scene sits underneath a warm, lit version clipped to a '
                 'hard-edged band -- a slanted shaft of light with window-mullion bars cut out of it -- '
                 'that sweeps across the frame.'),
    phrasings=('Sweep a hard beam of sunlight across this shot',
               'Add a dramatic light sweep, like light through a window',
               'Make part of the scene glow as a band of light passes over it'),
    api=('cv.ctx path + even-odd fill_rule for the clip',
         'cv.image(img, *box) for the dim and lit layers'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/hard-light-sweep.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)

"""3D shots: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/orbit-3d.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='orbit-3d',
    name='3D shots',
    family='camera',
    group='3D motion',
    category='Imagery and camera',
    order=5,
    definition='A pre-rendered 3D clip, composited like any other image.',
    description=('A pre-rendered 3D render (built offline, once) plays back as an ordinary clip inside the '
                 'film, composited exactly like any other picture, just fed a frame from a 3D shot instead '
                 'of a still image.'),
    phrasings=('Open on a 3D shot of the product, then cut to the UI',
               'Use the orbiting 3D render as the opening shot',
               'Composite the 3D clip behind the headline'),
    api=('vb.Clip(path)',
         'clip.frame(local_frame)',
         'cv.image(clip.frame(n), x, y, w, h)'),
    doc='skill/make-a-video/reference/3d.md',
    demo=Example('examples/capabilities/orbit-3d.py'),
)

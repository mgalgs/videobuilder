"""Parallax scene: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/parallax-scene.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='parallax-scene',
    name='Parallax scene',
    family='camera',
    group='Depth',
    category='Imagery and camera',
    order=7,
    aliases=('layered parallax', '2.5D depth', 'paper layer parallax', 'Disney multiplane'),
    definition='Flat layers slide at their own speeds as the camera pans, giving depth.',
    description=('A scene built from five flat layers drawn in code -- a far sky, hills, a row of trees, '
                 'the ground the character stands on, and grass and a signpost in the foreground -- each '
                 'moving at its own speed as the camera pans: the far ones barely, the near ones fast, the '
                 'foreground sweeping past in front. Every layer repeats with no seam, so the camera can '
                 'pan as far as it likes. Laid out separately for tall, wide and square videos.'),
    phrasings=('Give the background some depth as the camera pans',
               'Put the fox in a landscape with hills and trees behind it',
               'Have something pass in front of the camera, close up',
               'Pan across the scene slowly'),
    api=('parallax.Layer(depth, width, draw)  # draw(cv, x): one tile; depth 0 sky, 1 ground, >1 foreground',
         'parallax.draw(cv, layers, camera_x)  # far first; each tile repeated across the frame',
         'parallax.ridge(width, height, seed)  # a rolling skyline whose ends meet',
         'videobuilder.capabilities.camera.multiplane_camera.multiplane(cv, planes, camera)  # zoom into stacked planes',
         'videobuilder.capabilities.camera.multiplane_camera.Plane(z, draw)',
         'videobuilder.capabilities.camera.multiplane_camera.plane_transform(z, camera)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/parallax-scene.py'),
)

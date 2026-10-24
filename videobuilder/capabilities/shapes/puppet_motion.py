"""Puppet motion: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/puppet-motion.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='puppet-motion',
    name='Puppet motion',
    family='shapes',
    group='Characters & rigs',
    category='Motion',
    order=6,
    definition='One cut-out picture of a character, alive through movement alone.',
    description=('A cartoon character drawn once, as a single picture with its background cut out, comes '
                 'alive without a single new drawing: it breathes, sways and bobs, then crouches, hops, '
                 'stretches in the air, squashes as it lands and settles -- every move pivoting on its '
                 'feet, so it stays planted on the ground. All it needs is one cut-out picture: upload '
                 'one, or make one in the editor\'s Pictures panel with "Cut out the background" on. The '
                 'video moves the picture you give it; nothing is drawn at render time.'),
    phrasings=('Make the mascot feel alive, breathing and swaying a little',
               'Have the character hop, with a crouch first and a squash when it lands',
               "Animate my fox picture so it doesn't just sit there"),
    api=("FOX = vb.Puppet({'idle': 'fox.png'}, height=360)  # at import: downscaled once, feet measured",
         'FOX.draw(cv, pose, x, ground_y, sx=, sy=, lean=, angle=)  # every transform about the feet',
         'FOX.breath(n, period)  # a slow breath; a whole number of periods per loop',
         'vb.spring_at(f, fps, **vb.damped(0.25, hz=2.4))  # the landing settle'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/puppet-motion.py'),
)

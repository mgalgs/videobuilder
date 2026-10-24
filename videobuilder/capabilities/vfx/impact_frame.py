"""Impact frame: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/impact-frame.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='impact-frame',
    name='Impact frame',
    family='vfx',
    group='Editing & frame',
    category='Motion',
    order=10,
    definition='The anime hit: a push-in, a flash of silhouette and speed lines, a shake.',
    description=('A moment that lands hard, the way anime punctuates a hit: the camera pushes in fast, two '
                 'frames hold the subject as a flat black silhouette in a burst of speed lines on white, '
                 'then the picture comes back shaking and settles while the speed lines linger and fade. '
                 'Give it the moment ("when the fox lands the jump", "when the number hits one million"). '
                 'It is one bright flash, never a strobe: keep hits at least a second apart.'),
    phrasings=('Make the landing hit hard, like an anime impact',
               'Punctuate the moment the number hits one million',
               'Flash a silhouette with speed lines when it lands, then shake the screen'),
    api=('HIT = impact.Hit(at=frame)  # push, hold=2, settle, linger, zoom, shake, seed',
         ('HIT.draw(cv, n, scene, subject, centre=(x, y))  # scene(cv): the frame; subject(cv): the thing '
          'hit'),
         'impact.speed_lines(cv, cx, cy, seed, inner) / impact.silhouette(cv, draw, colour)',
         'impact.shake(n, at, frames, amount, seed) -> (dx, dy)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/impact-frame.py'),
    poster=60,  # the held silhouette
)

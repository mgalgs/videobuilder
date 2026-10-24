"""Walk in place: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/walk-in-place.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='walk-in-place',
    name='Walk in place',
    family='shapes',
    group='Characters & rigs',
    category='Motion',
    order=8,
    definition='A character walks while the camera follows, the ground scrolling past.',
    description=('The walk of cut-out TV animation: the character stays in the middle of the frame and '
                 'bobs on every step -- down with a little squash as each foot lands, up as it passes, '
                 'leaning forward -- while the ground and the hills scroll past underneath at a steady '
                 'speed, so it reads as walking. The steps land on the beat. There are no leg drawings: it '
                 'is a bounce on the spot made from one cut-out picture, not a real leg cycle, so it suits '
                 'a cartoon character better than a realistic one.'),
    phrasings=('Have the fox walk along while the camera follows it',
               'Make it walk on the beat, two steps a beat',
               'Scroll the ground past so it looks like it is going somewhere',
               'Give the walk a bit more bounce'),
    api=('g = FOX.walk(n, step=GRID.frames_per_beat / 2)  # Gait: lift, sx, sy, lean, phase',
         'FOX.draw(cv, pose, x, ground_y - g.lift, sx=g.sx, sy=g.sy, lean=g.lean)',
         'parallax.draw(cv, LAYERS, n * stride / step)  # the ground scrolls one stride a step'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/walk-in-place.py'),
)

"""Pose swaps: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/pose-swaps.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='pose-swaps',
    name='Pose swaps',
    family='shapes',
    group='Characters & rigs',
    category='Motion',
    order=7,
    aliases=('lip sync shapes', 'mouth chart'),
    definition='A character snaps between drawn poses on the beat, old-cartoon style.',
    description=('The limited-animation trick from old cartoons and anime: a character holds a drawn pose, '
                 'snaps to the next on a beat with a quick two- or three-frame pop and a few speed lines, '
                 'and holds again -- talking by flapping between a closed and an open mouth on the '
                 'syllables, blinking now and then, and breathing under every hold so it never looks '
                 'frozen. It needs several poses of the same character, each with its background cut out: '
                 'upload 3-6 poses drawn elsewhere, or make each one from the first picture as a reference '
                 "(the Pictures panel can't do that by itself yet). Poses that only change the mouth or "
                 'the eyes swap without a jump; the others are lined up by their feet. The video swaps the '
                 'pictures you give it; nothing is drawn at render time.'),
    phrasings=('Make the character talk, mouth flapping on the words',
               'Snap to the pointing pose on the beat, with a little pop',
               'Have it blink now and then so it looks alive',
               'Use my fox poses like an old cartoon: hold, snap, hold'),
    api=(("FOX = vb.Puppet({'idle': ..., 'talk': ..., 'blink': ..., 'point': ...}, height=340)  # poses "
          'lined up by their feet'),
         "pose, age = FOX.pose_at(n, [(0, 'idle'), (15, 'talk'), (19, 'idle'), (45, 'point')])  # holds",
         'age 0-2: a squash, overshoot, settle pop on the snap',
         'FOX.draw(cv, pose, x, ground_y, sx=, sy=)',
         'FOX.breath(n, period)  # under every hold',
         'videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.draw_face(cv, cx, cy, r)'
         '  # a code-drawn face, for when there are no uploaded poses',
         'videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.blinking(t, at=)',
         'videobuilder.capabilities.shapes.blink_and_mouth_shape_swap.mouth_at(t, shapes)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/pose-swaps.py'),
)

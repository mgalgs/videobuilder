"""Pop on the beat: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/pop-on-the-beat.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='pop-on-the-beat',
    name='Pop on the beat',
    family='principles',
    group='Timing & spacing',
    category='Motion',
    order=4,
    definition='A scale accent that lands exactly on the grid.',
    description=('A mark pops — a quick scale accent — exactly on each beat of the grid, the way a logo or '
                 'a stat should punctuate a cut instead of drifting past it.'),
    phrasings=('Make the logo pop on the beat',
               'Add a scale punch every beat, snapped to the grid',
               'Accent this on beat 2 and beat 4 only'),
    api=('vb.Grid.b(beat)',
         'vb.spring_at(f, fps, **vb.damped(...))',
         'GRID.frames_per_beat'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/pop-on-the-beat.py'),
)

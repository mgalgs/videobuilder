"""Stick figure: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/stick-figure.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Members, Source

CAPABILITY = Capability(
    id='stick-figure',
    name='Stick figure',
    family='shapes',
    group='Characters & rigs',
    category='Motion',
    order=9,
    aliases=('running loop', 'run in place'),
    definition='A stick-figure character, drawn in code, that acts out the idea.',
    description=('The explainer favourite: a round white head with a face, a small white body and thin '
                 'black arms and legs, drawn entirely in code, so no picture is needed. It walks and runs '
                 'with its feet planted, takes named poses (point, wave, shrug, think, push, sit, crouch, '
                 'hold, read, cheer, slump) and moves between them with a little wind-up and the arms and '
                 'head following through, wears an expression (happy, worried, determined, surprised, '
                 'thinking, sleepy, content, annoyed), blinks and breathes in every hold, talks in time '
                 'with a narration, and carries a sheet, a map, a mug, a phone, a pencil or a sign. A '
                 'matching set (the ground, a wall, a door, a desk, a hill path, a café table) finishes '
                 'the scene, or it stands over any picture.'),
    phrasings=('Use a stick figure to act this out',
               'Have the stick figure run, hit a wall, then think',
               'Make it look surprised, then point the way',
               'Sit it down with a coffee at the end, looking content'),
    api=("FIG = vb.Stick(height=300, ink='#111', fill='#fff')  # one figure, the same in every clip",
         ("FIG.act(n, [(0, 'stand'), (40, 'point'), (80, 'shrug', 12)])  # blends with overlap, breathes "
          'in holds'),
         "step = FIG.gait(n, 'walk')  # pose, x along the ground, lift; feet planted",
         ("FIG.draw(cv, pose, x, ground_y, face=FIG.face_at(n, keys), blink=FIG.blink(n), prop='mug', "
          'talk=vb.stick.mouth(voice, t))'),
         'vb.stick.wall(cv, FIG, x, ground_y)  # and ground, door, desk, hill_path, cafe'),
    doc='skill/make-a-video/reference/stick.md',
    demo=Example('examples/capabilities/stick-figure.py'),
    poster=130,
    members=Members(ids=('run-cycle',)),
    source=Source('https://x.com/Jason23818126/status/2112030757724340314', '@Jason23818126'),
)

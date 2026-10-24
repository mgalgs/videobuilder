"""Cuts locked to the music: built from videobuilder's own API, so this record only names it and demos
it with its worked example film, `examples/capabilities/beat-lock.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='beat-lock',
    name='Cuts locked to the music',
    family='sound',
    group='Music',
    category='Timing, sound and formats',
    order=1,
    aliases=('beat sync', 'edit to the beat', 'on the beat'),
    definition='Hard cuts land exactly on the beat, with a music bed.',
    description=('A music bed drives the cut points directly: every segment starts on a beat of the grid, '
                 'so the hard cuts land on the music instead of merely sitting near it.'),
    phrasings=('Cut this on the beat, with a music bed under it',
               'Lock the hard cuts to the grid, 120 bpm',
               'Add a placeholder music bed and cut to it'),
    api=('vb.Audio(path, gain_db=..., fade_out_frames=...)',
         "skill's make_track.py synth(bpm, beats, ...)",
         'Segment starts are beats, so cuts are on-grid by construction',
         'videobuilder.capabilities.sound.cut_to_the_beat.cut_to_the_beat(cv, n, grid, shots)',
         'videobuilder.capabilities.sound.cut_to_the_beat.beat_pulse(n, grid)',
         'videobuilder.capabilities.sound.cut_to_the_beat.beat_sounds(grid, id, hi)'),
    doc='skill/make-a-video/reference/music.md',
    demo=Example('examples/capabilities/beat-lock.py'),
)

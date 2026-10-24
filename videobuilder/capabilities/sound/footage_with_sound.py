"""Footage with its own sound: built from videobuilder's own API, so this record only names it and
demos it with its worked example film, `examples/capabilities/footage-with-sound.py` (an `Example`
demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='footage-with-sound',
    name='Footage with its own sound',
    family='sound',
    group='Mixing & editing',
    category='Timing, sound and formats',
    order=2,
    aliases=('audio ducking', 'sidechain ducking', 'dip the music'),
    definition='A clip plays with its sound while the music dips under it.',
    description=('A speaker clip cuts in and plays with its own sound, mixed with the music bed: the music '
                 'dips under the speech while the clip plays and comes back up when it ends, and the whole '
                 'mix is evened out to one loudness, so the voice is easy to hear without the music ever '
                 'cutting out.'),
    phrasings=('Use this clip with its sound, and bring the music down under the speech',
               'Let us hear the speaker, then bring the music back up after',
               'Cut between the interview clips and the graphics, with the music underneath'),
    api=('vb.Sound(path, at=, start=, frames=, fade_in_frames=, fade_out_frames=)',
         "ft = vb.footage(TIMELINE, 'segment', start=seconds)  # picture and sound in sync",
         'clip.frame(clip.frame_at(ft.seconds_at(n)))',
         'ft.sound(path) -> Film(sounds=(...))',
         ('vb.Audio(music, duck_db=-8)  # the music ducks while a sound plays; -8 for a voice-over, ramps '
          'and short-gap bridging are automatic')),
    doc='skill/make-a-video/reference/footage.md',
    demo=Example('examples/capabilities/footage-with-sound.py'),
    source=Source('https://www.youtube.com/watch?v=JOSJE6hQbdE', 'The Anomaly Archive'),
)

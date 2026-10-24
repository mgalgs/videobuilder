"""Narration: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/narration.py` (an `Example` demo: see schema.py)."""
from ... import speech
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='narration',
    name='Narration',
    family='sound',
    group='Mixing & editing',
    category='Timing, sound and formats',
    order=3,
    definition='A generated voiceover, captioned, with a character that talks.',
    description=('A voiceover read from a short script by a text-to-speech voice (Kokoro, open weights), '
                 'made once and kept with the video like any other sound file: the captions follow it '
                 "phrase by phrase, and a cut-out character's mouth opens and shuts with the voice. To ask "
                 'for it, give the words to say, one phrase or sentence per line, and the kind of voice (a '
                 'calm American woman, a British man...). If a name comes out wrong, say how it should '
                 'sound ("Galgs rhymes with dolls") and the builder respells it for the voice while the '
                 'captions keep the real spelling. The voice reads the words as written; it does not act '
                 'them.'),
    phrasings=('Add a voiceover that says this script, with captions under it',
               'Use a calm British voice, a little slower',
               'Make the fox say this line, mouth moving with the words',
               'It says our product name wrong: it should sound like "loo-men"'),
    api=(('python -m videobuilder say script.txt --out assets/voice.wav [--voice af_heart] [--speed 1.0]  '
          '# once; commit the .wav, .vtt, .json and the script'),
         ('[Lumen](/lˈuːmən/) in the script, or --say Lumen=Loomen  # fix a pronunciation; say --phonemes '
          'shows it'),
         "VOICE = vb.speech.load('assets/voice.wav'); Film(sounds=(VOICE.sound(at=frame),))",
         'vb.captions.draw(cv, VOICE.track_at(frame, fps), n / fps)  # a cue per phrase',
         "mouth = VOICE.mouth(fps, at=frame, frames=TOTAL); pose = 'talk' if mouth[n] else 'idle'"),
    doc='skill/make-a-video/reference/narration.md',
    demo=Example('examples/capabilities/narration.py'),
    settings=speech.narration_settings(),  # shared with sound/voiceover.py: the two offer the same controls
)

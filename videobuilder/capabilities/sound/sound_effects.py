"""Sound effects: built from videobuilder's own API, so this record only names it and demos it with its
worked example film, `examples/capabilities/sound-effects.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Members, Source

CAPABILITY = Capability(
    id='sound-effects',
    name='Sound effects',
    family='sound',
    group='Sound effects',
    category='Timing, sound and formats',
    order=4,
    definition='A whoosh, a click, a ding and a hit, each on its frame.',
    description=('Ready-made sound effects (whooshes, clicks and taps, pops, dings, risers, hits, sub '
                 'drops, shimmers) put on the exact frame of the motion they sell: a whoosh peaks as a '
                 'card whips past, a click lands on the press, a ding on the notification landing, a hit '
                 'on the impact frame. They sit in the mix with the music and dip under a voice like it '
                 'does. To ask for one, say what should make a sound and when ("a whoosh on the whip pan", '
                 '"a click when the button is pressed"); a few well-placed sounds read better than one on '
                 'every cut.'),
    phrasings=('Add a whoosh when the card flies in',
               'Put a click on each button press',
               'Make the logo land with a hit',
               'Add a soft ding when the notification appears'),
    api=("vb.sfx.sound('whoosh_fast/tight', at=frame, dur=0.5, gain_db=-8)  # its peak on the frame",
         "vb.sfx.sound('fit/click/floss_lid', at=frame, align='onset')",
         "vb.sfx.sound('pro_notify/ding_2045', at=frame, note='G5')  # a tuned sound by note",
         "vb.sfx.find('whoosh', near_dur=0.8)  # by role",
         'Film(sounds=(...))',
         ('{"sfx": "pro_impact/short", "at": 120} in a timeline.json lane; "sound": "auto" on a whip or '
          'flash')),
    doc='skill/make-a-video/reference/sfx.md',
    demo=Example('examples/capabilities/sound-effects.py'),
    members=Members(
        ids=('whoosh', 'impact-hit', 'riser', 'sub-drop', 'success-chime', 'ui-sound-effects', 'typing-sounds',
             'foley', 'glitch-sound', 'reverse-cymbal'),
        noun=('effect', 'effects')),
    source=Source('https://x.com/LexnLin/status/2111927727318245426',
                  '@LexnLin',
                  upstream='https://github.com/Leonxlnx/earshot',
                  upstream_credit='Leon Lin (earshot, MIT)'),
)

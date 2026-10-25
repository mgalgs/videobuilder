# Narration: a generated voiceover

For a video that someone should hear talking: a voiceover read from a
script, captions that follow it, and optionally a cut-out character whose
mouth moves with it. The voice is Kokoro (open weights, Apache-2.0), run
once by `python -m videobuilder say`. The film loads the files `say` wrote
like any other sound; rendering never runs the model.

## Making the voice

Write the script into the project, one phrase or sentence per line
(`assets/voice.txt`; a line starting with `#` is a note, not spoken):

```
Meet Lumen.
It plans your day before you wake up.
```

```
python -m videobuilder say assets/voice.txt --out assets/voice.wav
```

This writes `assets/voice.wav` (24 kHz mono), `assets/voice.vtt` (one cue
per phrase) and `assets/voice.json` (each phrase's start and end, and the
inputs that made them), and prints the phrase times. **Commit all three and
the script.** Run it again after changing the script; with the same script
and settings it writes nothing, so it never churns the repo. `--force`
remakes it anyway.

- If the note that asked for this carries a `voice` or `speed` line under
  `narration` in "Capabilities the creator asked for", that is the
  director's own pick from the `#narration` chip's settings card -- pass it
  to `--voice`/`--speed` as given, not the defaults below.
- `--voice`: default `af_heart`, an even, clear American English voice.
  `--list-voices` lists them: the first letter is the language (`a` American
  English, `b` British English, `e` Spanish, `f` French, `h` Hindi, `i`
  Italian, `j` Japanese, `p` Brazilian Portuguese, `z` Mandarin), the second
  `f`/`m`. Good English ones: `af_heart`, `af_bella`, `am_michael`,
  `bf_emma`, `bm_george`.
- `--speed`: 0.5-2.0 (default 1.0). `--gap`: seconds of silence between
  phrases (default 0.35); a new line is also where the voice pauses.
- Times are measured from the audio, per phrase: Kokoro gives no word
  times, so the captions spread each phrase's words over it by length.
  Short phrases keep the highlight close.
- Without the model, `say` says what to install: `pip install
  'videobuilder[speech]'` and the two model files. In the videobuilder
  image they are already there.

## Fixing a mispronounced word

`say --phonemes` prints how each phrase will be read. Then either:

- **Respell it**: `--say Galgs=Gawlgz` (repeatable) or `--lexicon
  names.json` (`{"Galgs": "Gawlgz"}`), whole words, any case. The captions
  keep the real spelling.
- **Give the phonemes**, copied from `--phonemes` and edited: in the
  script, `[Lumen](/lˈuːmən/)` (Kokoro's own syntax: the word in brackets
  is captioned, the phonemes between the slashes are spoken), or
  `--say Lumen=/lˈuːmən/`. IPA typed by hand or copied from a dictionary
  is fine: the voice gets two-part sounds as Kokoro's single symbols
  (`ɔɪ` as `Y`, `aɪ` as `I`, `tʃ` as `ʧ`...), as `--phonemes` shows.

Put the flags you used in a comment at the top of the script, so the next
run makes the same voice.

A fix only counts if `--phonemes` shows it changed something: a respelling
that prints the same phonemes as the word itself (Freud and Froyd both give
`fɹˈYd`) changes nothing in the audio. Years from 1100 to 1999 already read
as years ("eighteen sixty-three"); write later ones as you want them said.

## Fixing a pause in the wrong place

Kokoro guesses its own phrasing, and inside a long subject it often
guesses wrong: "California's tax revenue rises and falls with the
economy." comes out as [California's tax revenue rises] [and falls with
the economy]. Listen to each phrase, and measure its pauses:

```
ffmpeg -i assets/voice.wav -af silencedetect=noise=-40dB:d=0.12 -f null -
```

Mark where the break belongs with `|` between words:

```
California's tax revenue | rises and falls with the economy.
```

The voice gets a comma there (`--phonemes` shows it) and nothing else
changes; the captions and the `.json` never show the mark. Don't reword a
correct script or add a visible comma to move a pause. `|` works next to
`[word](/phonemes/)`, inside the phonemes and in a respelling, and never
splits a phrase.

## Using it in the film

```python
VOICE = vb.speech.load(HERE / 'assets' / 'voice.wav')   # reads the .json and .vtt
AT = GRID.b(2)                                          # the film frame the voice starts on
TRACK = VOICE.track_at(AT, FPS)                          # captions on the film's clock
MOUTH = VOICE.mouth(FPS, at=AT, frames=TOTAL)            # per frame: is the mouth open?

FILM = vb.Film(..., sounds=(VOICE.sound(at=AT, fps=FPS),))
# in draw:
vb.captions.draw(cv, TRACK, n / FPS, font=..., safe=...)
FOX.draw(cv, 'talk' if MOUTH[n] else 'idle', x, ground_y)
```

- `VOICE.phrases` (text, start, end in seconds from the file's start) and
  `VOICE.frames(fps)` lay out segments around the voice: give each phrase's
  shot at least its phrase. With music, `vb.Audio(..., duck_db=-8)` dips it
  under the voice (see `footage.md`): the library ramps the dip in and out
  and bridges short gaps between phrases on its own, so don't hand-roll that.
- `MOUTH` opens near each syllable's peak and shuts in the dips, never for
  less than two frames; `vb.speech.holds(MOUTH)` turns it into
  `Puppet.pose_at` holds. Only blink while the mouth is shut.
- See `examples/capabilities/narration.py` for the whole thing.

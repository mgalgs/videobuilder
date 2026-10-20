# Sound effects: `vb.sfx`

Ready-made sound effects, each put on the exact frame of the motion it
sells: a whoosh on a whip pan, a click on a press, a hit on an impact
frame. The sounds are earshot's bank (MIT, by Leon Lin): made in code, a
few fitted from CC0 recordings, rendered once to small Opus files with each
take's onset, peak and end measured.

## Getting the pack

The sounds live outside the repo, in one pack (`vb-sfx-1`, about 23 MB):

    python -m videobuilder sfx fetch                 # download, check its sha256, unpack
    python -m videobuilder sfx list [--role whoosh] [--takes]
    python -m videobuilder sfx play-path whoosh_fast/tight--0.5s   # a take's file, to listen to

It is read from `$VIDEOBUILDER_SFX_DIR` (the editor's image has it in
/opt/vb-sfx), else `~/.cache/videobuilder/vb-sfx-1`. Without it, any use
of `vb.sfx` stops with one error naming the fetch command. Listen before
you choose: `play-path` prints the file to open.

## In a film

```python
WHOOSH = vb.sfx.sound('whoosh_fast/tight', at=PAN_MIDDLE, dur=0.5, gain_db=-8)
TAP = vb.sfx.sound('fit/click/floss_lid', at=PRESS, gain_db=-6)
DING = vb.sfx.sound('pro_notify/ding_2045', at=LANDS, note='G5', gain_db=-10)
HIT = vb.sfx.sound('pro_impact/short', at=IMPACT, gain_db=-8)
FILM = vb.Film(..., audio=vb.Audio('assets/music.wav', duck_db=-10), sounds=(WHOOSH, TAP, DING, HIT, VOICE.sound(at=0)))
```

- `at` is the film frame its **peak** lands on (the default; the loudest
  moment: a whoosh's pass, a hit's body), or its **onset** with
  `align='onset'` (where it starts: a click on the press frame, a riser's
  first breath). Peaks and onsets are measured, to the millisecond, so a
  sound can start a fraction of a frame before its frame. The `Film`
  places its sounds at its own fps, so `fps=` is needed only for a sound
  used outside a film.
- **Length.** A sound with several lengths (whooshes 0.25-2 s, risers,
  downlifters, sub drops, shimmers 0.5-4 s) takes the one nearest `dur`
  (seconds), cut to `dur` with a short fade if that one is longer. Without
  `dur`, the base take, whole. `variant='0.8s'` names a take exactly.
- **Note.** A tuned sound (dings, plucks, sub drops) takes `note='E5'`
  (`'C#5'`, `'Cs5'` and `'Db5'` are one note); asking for one it hasn't
  names the nearest.
- **Level.** `gain_db` is from the take's own level (every take peaks at
  -1 dBFS). Start whooshes and hits around -8 dB, clicks and taps around -6,
  dings and shimmers around -10 to -12 against music, and adjust by ear.
  The mix is evened out to one loudness, capped by its loudest peaks: a
  sound effect's peaks may be limited a few dB (the music dips under it for
  that moment), but a much hotter one makes the whole film quieter.
- **Under speech.** Sound effects don't duck the music; they dip with it
  while speech plays (`Audio.duck_db`). `through=True` keeps one at its
  level (a hit that must land over a line).
- **Finding one.** `vb.sfx.find('whoosh', near_dur=0.8)` lists a role's
  sounds, the nearest length first; `vb.sfx.roles()` the roles;
  `vb.sfx.get(id).takes` a sound's takes with their `peak_s`, `onset_s`,
  `dur_s`.

A sound before frame 0 or past the last frame is cut there.

**Hundreds are fine.** A key click per keystroke of a typed log, a tick per
line, five hundred placements reusing a few sounds: keep each one its own
`vb.sfx.sound(...)` in `sounds`. The render mixes them in one pass, and the
checks still find every one on its frame. Don't mix them into one file
yourself: a pre-mixed bed can't be checked sound by sound.

## Which sound for which moment

| moment | role | try |
|---|---|---|
| a whip pan, a fast move, a card flying in | whoosh (peak on the fastest frame, or the pan's middle) | `whoosh_fast/tight`, `whoosh_fast/crisp`, `fit/whoosh.short/bamboo_swish` |
| a big transition, a slow swell into a cut | whoosh | `whoosh_big/swell`, `pro_whoosh_big/swell` |
| text sliding in, a thin flick | swish | `swish/*`, `swipe/*` |
| an impact frame, a logo lock, a title slam | hit (peak on the impact) | `pro_impact/short`, `pro_impact/air`; `impact/*` have long tails: give `dur` |
| weight under a hit | sub drop (onset on the hit) | `pro_sub_drop/ref`, `pro_sub_drop/quick` |
| a cursor press, a button | click (onset or peak on the press) | `fit/click/floss_lid`, `pro_click/*` |
| a finger on glass, a light touch | tap | `pro_tap/soft`, `fit/land.light/finger_phone` |
| a switch flipping | toggle | `fit/snap/switch_flip`, `toggle/*` |
| an element popping in | pop | `pro_pop_in/round`, `fit/pop/mouth_plop` |
| hover, rows going by, a counter ticking | tick | `fit/tick/domino`, `pro_hover_tick/*` |
| a notification, a success | ding (a run steps up a semitone) | `pro_notify/ding_2045` with `note`, `pluck/kalimba` |
| a build into a reveal | riser (its peak, at its end, on the reveal) | `pro_riser/*`, `riser/swell` |
| energy leaving a moment | downlifter (onset just after it) | `downlifter/*` |
| sparkle, a shine, a glint | shimmer | `pro_shimmer/m0`, `shimmer/*` |
| a glitch transition | glitch (ends on the cut) | `pro_glitch/*` |
| typing | key, typing | `fit/key/medium`, `pro_typing_run/*` |
| a logo reveal in one gesture | logo sting | `logo_sting/*`, `pro_logo_sting/*` |

## Restraint

- **Not every cut.** Pick the few moments that matter: the hero move, the
  impact, the press the story turns on. Most cuts belong to the music.
- **Quiet under speech.** A voice wins; keep effects under it (they dip
  with the music) and move them off the words where you can.
- **One family per film.** Each sound has a `family`: `designed` (the
  `pro_` sounds, tight and gated), `classic`, or `fitted` (from real
  recordings). Keep to one, so the film sounds of a piece.
- **One gesture each.** A hit is one hit; don't stack three on a frame.
  A riser into a hit, a sub drop under it: that's the most to stack.

## In a film made of clips

A clip uses `vb.sfx` inside itself like any film. On the timeline, an Audio
lane item can be a sound effect, and a cut can ask for one (see
`films.md`):

```json
{"sfx": "whoosh_fast/tight", "at": 96, "frames": 15, "gain_db": -8}
"cut": {"transition": "whip", "frames": 8, "sound": "auto"}
```

## Checking

`check.py film.py --video` finds each sound effect in the rendered MP4's
sound (fitting its loudness envelope, and the other effects', to the mix)
and FAILs one that lands more than a frame from where it was put, or that
clips; it WARNs when the mix buries one too far to find (raise its gain or
listen) or the film ends before its tail does.

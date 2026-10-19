# Stick figure: a character drawn in code

For an explainer acted out by one simple character: a round white head
with a face, a small white body, thin black arms and legs. It reads the
map, runs, hits a wall, thinks, points the way, sits down with a coffee.
`vb.Stick` draws it from numbers on every frame, so there is no picture to
make, upload or cut out. The worked example is
`examples/capabilities/stick-figure.py`; the showcase's `stick` shot
(`examples/showcase_scenes/stick.py`) runs it into a wall.

## The rig

```python
FIG = vb.Stick(height=300, ink='#16171b', fill='#ffffff')   # the defaults: black on white, weight 0.03
FIG.draw(cv, 'stand', x, ground_y, face='happy', mark='hero')
```

- **Size** is one number, `height`: px from the soles to the top of the
  head, standing straight. **Colours** are `ink` (lines, face) and `fill`
  (head, body). `weight` is the line weight as a share of the height;
  `body='line'` swaps the rounded body for a single stroke.
- `draw(cv, pose, x, y)` stands the pose on the ground at `(x, y)` **by its
  lowest foot**, so every pose and every blend is on the ground with no
  bookkeeping; `lift` raises it (a jump). It returns a `Drawn`:
  `joints` (every joint's point on the canvas), `box`, and `prop` (the held
  prop's anchor). `FIG.joints(pose, x, y)` gives the same points without
  drawing, for placing things against the figure (a wall at its hand).
- **A pose is ten angles** (`vb.stick.Pose`): `lean`, `nod`, and for each
  front and back arm and leg, the limb and its elbow or knee. Limb angles
  read alike everywhere: 0 straight down, 90 straight ahead, 180 straight
  up, -90 straight behind. Arms are measured from the body (they lean with
  it), legs from the vertical. Limbs keep their length through any pose or
  blend. `front_` limbs are drawn over the body, `back_` limbs behind it;
  arms pass behind the head, hands on top.
- **Facing**: `facing=1` faces right, `-1` left (a mirror image; a sign's
  words still read). `FIG.turn(n, at, frames=6, start=1, end=-1)` gives the
  value through a turn: a quick squash to the side view and out the other
  way. `turn=` (0..1, default 0.35, three-quarter) slides the face toward
  where it faces.
- **Over a picture**: the head and body keep their own fill, so the figure
  reads over a Look's scene, a photo or a `vb.Picture`. On a busy one pass
  `halo='#ffffff'` for a light rim round every line.

## Expressions and poses

`vb.stick.expressions()`: `neutral`, `happy`, `worried`, `determined`,
`surprised`, `thinking`, `sleepy`, `content`, `annoyed`. An expression is a
`Face` of numbers (eye size, how open, gaze; brows' slant and lift; the
mouth's curve, opening, width, roundness, teeth), so two blend.
`vb.stick.face('happy', mouth='o', gaze_x=-1)` starts from a named one and
changes what you name; the mouths are `smile`, `flat`, `frown`, `open`,
`o`, `gritted`.

`vb.stick.names()`: the still poses `stand`, `point`, `wave`, `shrug`,
`think` (hand to chin), `push` (against a wall), `sit` (on a seat at
`FIG.seat()` px), `crouch`, `hold` (an object out at chest height), `read`
(a sheet in both hands), `cheer`, `slump`; and the cycles `walk`, `run`
and `wave`, which move on the frame number. An unknown name raises one
`ValueError` listing them all.

```python
pose = FIG.act(n, [(0, 'stand'), (36, 'point', 10), (90, 'shrug', 12)])
face = FIG.face_at(n, [(0, 'neutral'), (34, 'surprised', 4), (48, 'happy')])
FIG.draw(cv, pose, x, ground_y, face=face, blink=FIG.blink(n))
```

- `act(n, keys)` is a performance: `(frame, pose)` or `(frame, pose,
  frames)` keys, each moving from wherever the figure is into its pose
  over `frames` (default 10) and holding it. Every hold **breathes**
  (`FIG.alive`: the body rises and falls, the head drifts, the knees give
  as the weight shifts), so it is never frozen; pass `alive=False` for the
  bare poses.
- Each move has **overlap**: the body leads, the arms trail it by a quarter
  of the move and overshoot a little as they land, the head settles last
  on a spring. A big move (a crouch into a cheer) **winds up** the other way
  first; `FIG.move(a, b, age, frames, anticipate=)` controls that directly.
  `vb.stick.blend(a, b, t)` is the plain blend, exact at 0 and 1.
- `FIG.blink(n)` blinks every 2.6-4.8 s, seeded by `Stick(seed=)`: give two
  figures different seeds so they don't blink together.

## Walking and running

```python
step = FIG.gait(n, 'walk')            # or 'run'
FIG.draw(cv, step.pose, x0 + step.x, ground_y - step.lift)
```

Each foot plants and stays put while the body passes over it at a steady
speed, `FIG.speed('walk')` px a frame; `step.x` is how far it has gone. A
walk always has a foot down; a run leaves the ground between steps
(`step.lift`). A cycle is two steps: 1 s for a walk, 0.62 s for a run
(`period=`). To **walk in place** for a scrolling background, keep `x`
still and move the ground and backdrop by `step.x` (`parallax.draw(cv,
LAYERS, step.x)`): the feet still match the ground. To stop, key the stand
on a frame where both feet are down (a walk's phase 0 or 0.5:
`step.contact == 'both'`) so nothing slides.

## Talking

`vb.stick.mouth(timings, t)` is how open the mouth is at `t` seconds: shut
between words, and one open-and-shut flap a syllable inside each word.
`timings` is a narration (`vb.speech.load(...)`, whose words the captions
spread over each phrase), a captions `Track`, or `(text, start, end)`
tuples. Pass it as `talk=`, on the film's clock:

```python
VOICE = vb.speech.load(HERE / 'assets' / 'voice.wav')
TRACK = VOICE.track_at(AT, FPS)                        # the words on the film's clock
FIG.draw(cv, pose, x, y, face=face, talk=vb.stick.mouth(TRACK, n / FPS))
```

## Props

`prop='mug'`, or `vb.stick.prop(kind, text='', hand='front')`: `sheet`,
`map`, `mug`, `phone`, `pencil`, `sign` (with `text`). A prop is drawn at
its hand on every frame, in the figure's line style, so it stays attached
through any move. A `sheet` or `map` in the `read` pose is held open
between both hands; in one hand it is held up by its edge. A mug stays
upright whatever the arm does. In a walk, a prop in the `back` hand swings
behind the body.

## The scene kit

Backdrops in the same clean line style, each taking the figure as its
unit (its height, ink, fill and line weight), so the set always matches
the cast. Each returns the Box it drew; `fill=None` leaves a piece open
over a picture.

| Call | Draws |
|---|---|
| `vb.stick.ground(cv, FIG, y)` | the ground line, across the frame |
| `vb.stick.shadow(cv, FIG, x, y, k=1)` | a soft shadow under the feet (`k` < 1 in a jump) |
| `vb.stick.wall(cv, FIG, x, y, height=1.25)` | a brick wall, its face at `x` (`facing=-1` for one on the left) |
| `vb.stick.door(cv, FIG, x, y, open=0)` | a door in its frame, swinging open |
| `vb.stick.desk(cv, FIG, x, y)` | a desk with a drawer and a laptop |
| `vb.stick.hill_path(cv, FIG, x0, x1, y)` | a hill with a path up it and a flag on top |
| `vb.stick.cafe(cv, FIG, x, y, mug=True)` | a café chair (seat at `FIG.seat()`) and a table, for `sit` at `x` |

Draw the chair before the figure and anything it stands in front of after.
Put a wall where the push pose's hands land:
`wall_x = x + FIG.joints('push', 0, 0)['front_hand'][0]`.

## Acting a narrated beat

A stick-figure explainer is a narration acted out, one beat (a line, or
half a line) per pose:

1. **Pose on the stressed word.** Find the word the line turns on (in "it
   doesn't get you *anywhere*", *anywhere*) in the narration's word times
   and land the pose there: start the move `frames` earlier, so it arrives
   on the word rather than starting on it. The face can lead the body by a
   few frames: the thought shows before the gesture.
2. **Hold.** Let the pose breathe through the rest of the line; don't
   fidget. One gesture a beat reads; three blur.
3. **Anticipate the next.** Key the next move to start just before the
   next stressed word, from the hold: a crouch before a jump, a lean back
   before a run, a look before a point. Big moves wind up on their own.
4. **Cut on the action** if the shot changes: the figure starts the move
   in one shot and finishes it in the next, at the same size and place.

Talk (`talk=`) only when the figure itself is speaking; under a narrator,
keep its mouth to the expression. Sound sells the beats: a whoosh as a run
starts, a soft hit on the wall, a pop on a reveal (`reference/sfx.md`).

## One figure through a film

A film of several clips casts the same figure in all of them. Put the
figure in the film's bible (`reference/films.md`): a
`bible/characters/<name>.md` with its `vb.Stick(...)` line, its height for
a wide shot, its seed, the way it faces when it goes forward, and the
expressions and props it owns. Build it the same way in every clip:

- the same `height` for the same framing (a close-up scales it with
  `scale=`, not a new height), the same `ink`, `fill`, `weight` and `body`;
- the same `seed`, so its blinks don't jump at a cut;
- the same ground height across a sequence, and the same facing for the
  same direction of travel (left to right is going forward);
- its props and backdrops from the kit, which take their style from the
  figure.

Copying a `FIG = vb.Stick(...)` line into each clip's `film.py`, with the
bible's numbers, is enough: the figure has no files to keep in step.

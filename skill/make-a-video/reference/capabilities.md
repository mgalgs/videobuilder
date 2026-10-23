<!-- GENERATED from videobuilder/capabilities/__init__.py by `sheet_markdown()`. Do not hand-edit;
     regenerate with `python -m videobuilder capabilities sheet > skill/make-a-video/reference/capabilities.md` after changing the catalog. -->
# Capabilities catalog

What videobuilder can already do, with a worked example for each. Reach for one of these before inventing an effect. Adding a capability later means adding one entry to `CATALOG` in `videobuilder/capabilities/__init__.py` and one demo film beside the others in `examples/capabilities/`; this file and the `/capabilities` page are both generated from that single catalog.

## Motion

### Eased entrances

**What it looks like:** The named motion tokens, compared side by side. Five named easing curves — videobuilder's motion tokens — each sliding a chip into place on its own row, so their character is easy to tell apart: a fast settle, a restrained glide, a small overshoot.

**When to use it:** reach for this when a director says something like:
- "Ease this in fast, then let it settle gently"
- "Use a restrained entrance, nothing bouncy"
- "Make the exit quicker than the entrance, and a little brisker"

**How to build it:**
- `vb.ease_out_expo`
- `vb.ease_out_quint`
- `vb.ease_in_out_quart`
- `vb.ease_out_back`
- `vb.ease_in_expo`
- `vb.interpolate(f, keys, values, ease=...)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/eased-entrances.py` — read it before writing something similar from scratch.

### Springs with character

**What it looks like:** One spring, three damping ratios: firm to playful. The same spring drop at three damping ratios — 1.0 (no bounce), 0.6 (restrained) and 0.3 (playful) — landing side by side so the difference in character is visible, not just described.

**When to use it:** reach for this when a director says something like:
- "Drop this in with a playful spring, a bit of bounce"
- "Use a firm landing, no bounce"
- "Make it bouncier, more cartoonish"

**How to build it:**
- `vb.spring_at(f, fps, **vb.damped(ratio, hz=2.0))`
- `vb.critical(stiffness)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/springs-with-character.py` — read it before writing something similar from scratch.

### Staggered reveals

**What it looks like:** A list that cascades in, one item after the next. List chips reveal in sequence, each starting while the one before it is still mid-flight, instead of all arriving at once — the cascade that makes a list of features or steps read as a group.

**When to use it:** reach for this when a director says something like:
- "Stagger these in as a list, cascading"
- "Don't pop them all in at once; stagger it"
- "Reveal the words one at a time, staggered"

**How to build it:**
- `vb.spring_at(f - delay, fps, **vb.damped(...))`
- `per-item frame delay (40-80ms list items)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/staggered-reveals.py` — read it before writing something similar from scratch.

### Pop on the beat

**What it looks like:** A scale accent that lands exactly on the grid. A mark pops — a quick scale accent — exactly on each beat of the grid, the way a logo or a stat should punctuate a cut instead of drifting past it.

**When to use it:** reach for this when a director says something like:
- "Make the logo pop on the beat"
- "Add a scale punch every beat, snapped to the grid"
- "Accent this on beat 2 and beat 4 only"

**How to build it:**
- `vb.Grid.b(beat)`
- `vb.spring_at(f, fps, **vb.damped(...))`
- `GRID.frames_per_beat`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/pop-on-the-beat.py` — read it before writing something similar from scratch.

### Character motion

**What it looks like:** Anticipation, squash and stretch, and follow-through. A hopping shape anticipates before it leaps (a crouch), stretches in the air, squashes on landing, and settles with a little follow-through — the full vocabulary from the animator's handbook, timed in frames.

**When to use it:** reach for this when a director says something like:
- "Give this hop some anticipation and squash and stretch"
- "Make the landing squash, then settle with follow-through"
- "This motion feels flat; add some character to it"

**How to build it:**
- `vb.interpolate`
- `vb.spring_at(f, fps, **vb.damped(0.22, hz=2.2))  # follow-through`
- `frame-level timing in reference/motion.md`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/character-motion.py` — read it before writing something similar from scratch.

### Puppet motion

**What it looks like:** One cut-out picture of a character, alive through movement alone. A cartoon character drawn once, as a single picture with its background cut out, comes alive without a single new drawing: it breathes, sways and bobs, then crouches, hops, stretches in the air, squashes as it lands and settles -- every move pivoting on its feet, so it stays planted on the ground. All it needs is one cut-out picture: upload one, or make one in the editor's Pictures panel with "Cut out the background" on. The video moves the picture you give it; nothing is drawn at render time.

**When to use it:** reach for this when a director says something like:
- "Make the mascot feel alive, breathing and swaying a little"
- "Have the character hop, with a crouch first and a squash when it lands"
- "Animate my fox picture so it doesn't just sit there"

**How to build it:**
- `FOX = vb.Puppet({'idle': 'fox.png'}, height=360)  # at import: downscaled once, feet measured`
- `FOX.draw(cv, pose, x, ground_y, sx=, sy=, lean=, angle=)  # every transform about the feet`
- `FOX.breath(n, period)  # a slow breath; a whole number of periods per loop`
- `vb.spring_at(f, fps, **vb.damped(0.25, hz=2.4))  # the landing settle`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/puppet-motion.py` — read it before writing something similar from scratch.

### Pose swaps

**What it looks like:** A character snaps between drawn poses on the beat, old-cartoon style. The limited-animation trick from old cartoons and anime: a character holds a drawn pose, snaps to the next on a beat with a quick two- or three-frame pop and a few speed lines, and holds again -- talking by flapping between a closed and an open mouth on the syllables, blinking now and then, and breathing under every hold so it never looks frozen. It needs several poses of the same character, each with its background cut out: upload 3-6 poses drawn elsewhere, or make each one from the first picture as a reference (the Pictures panel can't do that by itself yet). Poses that only change the mouth or the eyes swap without a jump; the others are lined up by their feet. The video swaps the pictures you give it; nothing is drawn at render time.

**When to use it:** reach for this when a director says something like:
- "Make the character talk, mouth flapping on the words"
- "Snap to the pointing pose on the beat, with a little pop"
- "Have it blink now and then so it looks alive"
- "Use my fox poses like an old cartoon: hold, snap, hold"

**How to build it:**
- `FOX = vb.Puppet({'idle': ..., 'talk': ..., 'blink': ..., 'point': ...}, height=340)  # poses lined up by their feet`
- `pose, age = FOX.pose_at(n, [(0, 'idle'), (15, 'talk'), (19, 'idle'), (45, 'point')])  # holds`
- `age 0-2: a squash, overshoot, settle pop on the snap`
- `FOX.draw(cv, pose, x, ground_y, sx=, sy=)`
- `FOX.breath(n, period)  # under every hold`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/pose-swaps.py` — read it before writing something similar from scratch.

### Walk in place

**What it looks like:** A character walks while the camera follows, the ground scrolling past. The walk of cut-out TV animation: the character stays in the middle of the frame and bobs on every step -- down with a little squash as each foot lands, up as it passes, leaning forward -- while the ground and the hills scroll past underneath at a steady speed, so it reads as walking. The steps land on the beat. There are no leg drawings: it is a bounce on the spot made from one cut-out picture, not a real leg cycle, so it suits a cartoon character better than a realistic one.

**When to use it:** reach for this when a director says something like:
- "Have the fox walk along while the camera follows it"
- "Make it walk on the beat, two steps a beat"
- "Scroll the ground past so it looks like it is going somewhere"
- "Give the walk a bit more bounce"

**How to build it:**
- `g = FOX.walk(n, step=GRID.frames_per_beat / 2)  # Gait: lift, sx, sy, lean, phase`
- `FOX.draw(cv, pose, x, ground_y - g.lift, sx=g.sx, sy=g.sy, lean=g.lean)`
- `parallax.draw(cv, LAYERS, n * stride / step)  # the ground scrolls one stride a step`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/walk-in-place.py` — read it before writing something similar from scratch.

### Stick figure

**What it looks like:** A stick-figure character, drawn in code, that acts out the idea. The explainer favourite: a round white head with a face, a small white body and thin black arms and legs, drawn entirely in code, so no picture is needed. It walks and runs with its feet planted, takes named poses (point, wave, shrug, think, push, sit, crouch, hold, read, cheer, slump) and moves between them with a little wind-up and the arms and head following through, wears an expression (happy, worried, determined, surprised, thinking, sleepy, content, annoyed), blinks and breathes in every hold, talks in time with a narration, and carries a sheet, a map, a mug, a phone, a pencil or a sign. A matching set (the ground, a wall, a door, a desk, a hill path, a café table) finishes the scene, or it stands over any picture.

**When to use it:** reach for this when a director says something like:
- "Use a stick figure to act this out"
- "Have the stick figure run, hit a wall, then think"
- "Make it look surprised, then point the way"
- "Sit it down with a coffee at the end, looking content"

**How to build it:**
- `FIG = vb.Stick(height=300, ink='#111', fill='#fff')  # one figure, the same in every clip`
- `FIG.act(n, [(0, 'stand'), (40, 'point'), (80, 'shrug', 12)])  # blends with overlap, breathes in holds`
- `step = FIG.gait(n, 'walk')  # pose, x along the ground, lift; feet planted`
- `FIG.draw(cv, pose, x, ground_y, face=FIG.face_at(n, keys), blink=FIG.blink(n), prop='mug', talk=vb.stick.mouth(voice, t))`
- `vb.stick.wall(cv, FIG, x, ground_y)  # and ground, door, desk, hill_path, cafe`
- Read `skill/make-a-video/reference/stick.md`.

**Worked example:** `examples/capabilities/stick-figure.py` — read it before writing something similar from scratch.

### Impact frame

**What it looks like:** The anime hit: a push-in, a flash of silhouette and speed lines, a shake. A moment that lands hard, the way anime punctuates a hit: the camera pushes in fast, two frames hold the subject as a flat black silhouette in a burst of speed lines on white, then the picture comes back shaking and settles while the speed lines linger and fade. Give it the moment ("when the fox lands the jump", "when the number hits one million"). It is one bright flash, never a strobe: keep hits at least a second apart.

**When to use it:** reach for this when a director says something like:
- "Make the landing hit hard, like an anime impact"
- "Punctuate the moment the number hits one million"
- "Flash a silhouette with speed lines when it lands, then shake the screen"

**How to build it:**
- `HIT = impact.Hit(at=frame)  # push, hold=2, settle, linger, zoom, shake, seed`
- `HIT.draw(cv, n, scene, subject, centre=(x, y))  # scene(cv): the frame; subject(cv): the thing hit`
- `impact.speed_lines(cv, cx, cy, seed, inner) / impact.silhouette(cv, draw, colour)`
- `impact.shake(n, at, frames, amount, seed) -> (dx, dy)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/impact-frame.py` — read it before writing something similar from scratch.

### Overlap transitions

**What it looks like:** One segment slides over the outgoing one — no hard cut. Instead of a hard cut, the next scene starts on its own beat while the one before it keeps drawing underneath for a few more frames: a transition built into the timeline itself, not a crossfade bolted on.

**When to use it:** reach for this when a director says something like:
- "Transition between these, not a hard cut"
- "Slide the end card in over the previous scene, overlapping for a beat"
- "Keep the previous scene visible while the next one arrives"

**How to build it:**
- `vb.Segment(..., overlap=k)`
- `Timeline.live(n) -> Shots back to front`
- `Shot.exit`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/overlap-transitions.py` — read it before writing something similar from scratch.

### Drawn-on diagram

**What it looks like:** A whiteboard diagram drawn stroke by stroke, pen tracked by camera. A small whiteboard diagram -- boxes, arrows, an icon, handwritten-looking labels -- draws on stroke by stroke with a little hand jitter, the camera tracking the pen across a board bigger than the frame, ending in a pull-back that shows the whole board at once.

**When to use it:** reach for this when a director says something like:
- "Draw this diagram on stroke by stroke, like a whiteboard"
- "Track the camera on the pen as it draws, then pull back"
- "Give the lines a bit of hand-drawn wobble, not perfectly straight"

**How to build it:**
- `videobuilder.paths.reveal(points, fraction)`
- `videobuilder.paths.jitter(points, seed)`
- `cv.layer(dx=.., dy=.., scale=..)  # the tracking camera`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/drawn-on-diagram.py` — read it before writing something similar from scratch.

### Outline morph

**What it looks like:** One outline smoothly becomes the next, not a cut. A circle turns into a document icon and back, its outline resampled to match point for point and interpolated with a smooth ease while its colour travels along -- one idea turning into the next instead of a hard cut between two shapes.

**When to use it:** reach for this when a director says something like:
- "Don't cut between these icons, morph one into the other"
- "Turn the circle into the document shape smoothly"
- "Let the colour shift as the shape changes, not just the outline"

**How to build it:**
- `videobuilder.paths.morph(a, b, t, closed=True)`
- `videobuilder.paths.draw(cv, points, colour, fill=True)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/outline-morph.py` — read it before writing something similar from scratch.

## Type and data

### Kinetic typography

**What it looks like:** Balanced wrapping, word-by-word reveal, live weight. A headline wraps with balanced line breaks, reveals word by word, and its variable-font weight itself animates in — all real text layout, not an image of text.

**When to use it:** reach for this when a director says something like:
- "Reveal this headline word by word, with neatly balanced line breaks"
- "Animate the weight in as it lands, thin to bold"
- "Make the type itself the motion here"

**How to build it:**
- `text.wrap(copy, font, width, balance=True)`
- `vb.Font(..., weight=interpolated)`
- `text.draw`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/kinetic-typography.py` — read it before writing something similar from scratch.

### Word-timed captions

**What it looks like:** Captions that follow the words as they are spoken. A speaker's words run along the bottom of the clip one short line at a time, each line measured to fit the frame: the word being spoken lights up in yellow as it is said, and a chosen keyword stays green, so the captions keep pace with the voice instead of sitting there as a block of text.

**When to use it:** reach for this when a director says something like:
- "Add captions that follow along word by word"
- "Highlight each word in yellow as it is said"
- "Make the word "mornings" stand out in green in the captions"

**How to build it:**
- `vb.captions.parse(text) / vb.captions.load(path)  # .vtt or .srt, word times kept`
- `track.slice(a, b).shift(at - a)  # a clip cut from a longer source`
- `vb.captions.draw(cv, track, t, keywords={...}, font=..., safe=...)`
- Read `skill/make-a-video/reference/captions.md`.

**Worked example:** `examples/capabilities/word-timed-captions.py` — read it before writing something similar from scratch.

### Terminal log

**What it looks like:** A terminal or chat log that types, prints and scrolls. A running log in a window, like an agent at work in a terminal: its thinking in one style, its commands typed at a prompt key by key with an uneven human rhythm, their output appearing whole in another colour. Long lines wrap; once the window is full it eases up a line at a time and old lines leave at the top. Every keystroke can click and every printed line tick, hundreds of sounds if the session is long.

**When to use it:** reach for this when a director says something like:
- "Show the agent's session as a terminal, typing and scrolling"
- "Put its thinking in grey italics and the commands in white after a prompt"
- "Let the output scroll up as new lines arrive"
- "Add a key click for every letter typed"

**How to build it:**
- `vb.terminal.Kind(vb.Font(mono, 28, style='italic'), colour, prefix='$ ', typed=True)`
- `events = vb.terminal.paced([(kind, text), ...], KINDS)  # or (t, kind, text) by hand`
- `LOG = vb.TerminalLog(events, KINDS); LOG.draw(cv, t, box)`
- `Film(sounds=LOG.sounds(at=0, fps=FPS))`
- Read `skill/make-a-video/reference/terminal.md`.

**Worked example:** `examples/capabilities/terminal-log.py` — read it before writing something similar from scratch.

### Numbers that count up

**What it looks like:** A hero stat counts from zero to its final value. A big number counts up to its final value on a spring, the way a benchmark or a result should land: with weight, not just appearing.

**When to use it:** reach for this when a director says something like:
- "Count this number up to 2.4x"
- "Make the stat count up as it lands, not just appear"
- "Count up to the final value over the first second"

**How to build it:**
- `vb.spring_at / vb.interpolate drives the displayed value`
- `f'{value * min(1, p):.1f}'`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/counting-numbers.py` — read it before writing something similar from scratch.

### Bar charts

**What it looks like:** Bars grow on the beat, each with a direct label. A bar chart grows its bars on their own beats, with the value labelled directly at the end of each bar (not a legend) so it reads correctly even without colour.

**When to use it:** reach for this when a director says something like:
- "Chart these as bars growing on the beat, direct labels"
- "No legend — label each bar directly"
- "Grow the hero bar last so it lands on the verdict"

**How to build it:**
- `cv.rect(..., radius=..., alpha=...)`
- `vb.spring_at for bar growth`
- `text.draw for direct labels`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/bar-charts.py` — read it before writing something similar from scratch.

### Gauges and rings

**What it looks like:** An arc fills to a reading, with a readout in the centre. A ring gauge sweeps from empty to its reading as an arc, with the number centred inside it — the shape for a single score, percentage or level rather than a comparison.

**When to use it:** reach for this when a director says something like:
- "Show this as a ring gauge filling to 72%"
- "Use an arc readout, not a bar, for a single score"
- "Sweep the gauge in on the beat"

**How to build it:**
- `cv.arc(cx, cy, r, a0, a1, colour, width=...)`
- `cv.sector(...)`
- `vb.spring_at drives the sweep angle`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/gauges-and-rings.py` — read it before writing something similar from scratch.

### Self-drawing line chart with a callout

**What it looks like:** Axes first, the line draws itself on, then one point is called out. Honest axes appear first, then every series draws itself on along its own path -- the background series in grey, only the hero series in colour -- and once it lands, one callout (a dot, a leader line and a short label) points at the single point that matters.

**When to use it:** reach for this when a director says something like:
- "Draw the axes first, then let the line draw itself on"
- "Keep the other lines grey, only highlight the hero line"
- "Call out the final point with a dot and a short label"

**How to build it:**
- `videobuilder.paths.reveal(points, fraction)`
- `videobuilder.paths.draw(cv, points, colour, width=...)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/line-chart-callout.py` — read it before writing something similar from scratch.

## Imagery and camera

### Camera on a screenshot

**What it looks like:** A window pans and zooms across a captured screen. A camera window pans and zooms across a (generated) screenshot, with a navbar strip pinned to the top of the window while the page itself scrolls underneath it.

**When to use it:** reach for this when a director says something like:
- "Pan and zoom across this screenshot, pin the navbar"
- "Push in on the pricing table, then pan down"
- "Keep the header pinned while the camera scrolls the page"

**How to build it:**
- `cv.view(img, box, center=, scale=, radius=)`
- `vb.log_lerp(a, b, p)  # even zoom`
- `view.pin(src, y=box.y)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/camera-on-a-screenshot.py` — read it before writing something similar from scratch.

### Redrawn product UI

**What it looks like:** A crisp vector screen, redrawn from measured blocks. A product screen redrawn as vector shapes and real text instead of a captured bitmap: crisp at any size, built from measured blocks stacked edge to edge.

**When to use it:** reach for this when a director says something like:
- "Redraw this screen instead of using a screenshot"
- "Rebuild the settings panel as crisp vector UI"
- "Keep this sharp at every size — redraw it, don't capture it"

**How to build it:**
- `Box.stack(heights, gap=..., align="top")`
- `cv.rect / cv.outline / text.draw for each block`
- Read `skill/make-a-video/reference/redrawn-ui.md`.

**Worked example:** `examples/capabilities/redrawn-product-ui.py` — read it before writing something similar from scratch.

### Image treatments

**What it looks like:** Cover and contain crops, rounded clips, soft shadows. The same generated image shown cover-cropped, contain-fitted, clipped to a rounded rect and lifted with a soft shadow — the box-model moves for putting a picture in a layout.

**When to use it:** reach for this when a director says something like:
- "Cover-crop this image into the card"
- "Fit it contain, with rounded corners and a soft shadow"
- "Give this picture a drop shadow, like a card"

**How to build it:**
- `Box.cover(w, h)`
- `Box.contain(w, h)`
- `cv.clip(x, y, w, h, radius=...)`
- `cv.shadow(...)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/image-treatments.py` — read it before writing something similar from scratch.

### Generated art

**What it looks like:** Cairo paths and gradients, seeded so they repeat. A procedural pattern drawn straight from cairo paths and a gradient, from a seeded random source so the same look renders the same way every time — no stock art, no network.

**When to use it:** reach for this when a director says something like:
- "Generate a background pattern, not a stock image"
- "Use a generated pattern that renders exactly the same every time"
- "Draw this as paths and a gradient, not a bitmap"

**How to build it:**
- `cv.ctx  # raw cairo Context`
- `cairo.LinearGradient / RadialGradient`
- `random.Random(seed)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/generated-art.py` — read it before writing something similar from scratch.

### 3D shots

**What it looks like:** A pre-rendered 3D clip, composited like any other image. A pre-rendered 3D render (built offline, once) plays back as an ordinary clip inside the film, composited exactly like any other picture, just fed a frame from a 3D shot instead of a still image.

**When to use it:** reach for this when a director says something like:
- "Open on a 3D shot of the product, then cut to the UI"
- "Use the orbiting 3D render as the opening shot"
- "Composite the 3D clip behind the headline"

**How to build it:**
- `vb.Clip(path)`
- `clip.frame(local_frame)`
- `cv.image(clip.frame(n), x, y, w, h)`
- Read `skill/make-a-video/reference/3d.md`.

**Worked example:** `examples/capabilities/orbit-3d.py` — read it before writing something similar from scratch.

### Hard-light sweep

**What it looks like:** A hard-edged band of light sweeps across the shot. A dim, shadowed version of the scene sits underneath a warm, lit version clipped to a hard-edged band -- a slanted shaft of light with window-mullion bars cut out of it -- that sweeps across the frame.

**When to use it:** reach for this when a director says something like:
- "Sweep a hard beam of sunlight across this shot"
- "Add a dramatic light sweep, like light through a window"
- "Make part of the scene glow as a band of light passes over it"

**How to build it:**
- `cv.ctx path + even-odd fill_rule for the clip`
- `cv.image(img, *box) for the dim and lit layers`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/hard-light-sweep.py` — read it before writing something similar from scratch.

### Parallax scene

**What it looks like:** Flat layers slide at their own speeds as the camera pans, giving depth. A scene built from five flat layers drawn in code -- a far sky, hills, a row of trees, the ground the character stands on, and grass and a signpost in the foreground -- each moving at its own speed as the camera pans: the far ones barely, the near ones fast, the foreground sweeping past in front. Every layer repeats with no seam, so the camera can pan as far as it likes. Laid out separately for tall, wide and square videos.

**When to use it:** reach for this when a director says something like:
- "Give the background some depth as the camera pans"
- "Put the fox in a landscape with hills and trees behind it"
- "Have something pass in front of the camera, close up"
- "Pan across the scene slowly"

**How to build it:**
- `parallax.Layer(depth, width, draw)  # draw(cv, x): one tile; depth 0 sky, 1 ground, >1 foreground`
- `parallax.draw(cv, layers, camera_x)  # far first; each tile repeated across the frame`
- `parallax.ridge(width, height, seed)  # a rolling skyline whose ends meet`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/parallax-scene.py` — read it before writing something similar from scratch.

## Looks

### Looks

**What it looks like:** Named art styles any video can ask for by name, each moving its own way. Named art styles any video can ask for by name ("make it pop art", "try a few looks"), each with its own signature motion, in two kinds. A scene look repaints a picture the video describes as a few shapes with roles (sky, water, land, buildings, figures, lights, the sun and a beacon); a filter look restyles whatever the video draws -- a photo, a screen capture, footage -- every pixel, frame by frame. They share names where the style carries over, so "pop art" finds both. Creators can add scene looks of their own.

**When to use it:** reach for this when a director says something like:
- "Make it look like pop art"
- "Try a few different looks on this and let me pick"
- "Make my product demo look like an 8-bit game"
- "Give it a dreamy surreal look, things melting"

**How to build it:**
- `looks.Scene(w, h, [looks.Region(role, points), ...], horizon=, sun=(x, y, r), beacon=(x, y))`
- `looks.paint(cv, 'pop-art', scene, t, age)  # a scene look`
- `looks.names() / looks.get(name)`
- `with looks.filter(cv, 'pop-art', t): draw_as_usual(n, cv)  # a filter look, on any picture`
- `looks.filters() / looks.get_filter(name)`
- `looks.relay(cv, scene, t, names, hold=2.0)  # try several in turn`
- `looks.motion_floor(film, start, end) >= looks.FLOOR`
- Read `skill/make-a-video/reference/looks.md`.

**Worked example:** `examples/capabilities/looks.py` — read it before writing something similar from scratch.

**The looks** (14; ask for any look by name):

*Scene looks*, for a picture the video draws: it describes the shapes, the look paints them:

- **Post-Impressionist swirl** (`swirl`): Thick dabs of paint; the sky turns in eddies. Ask: "Make it look like a swirling oil painting". Build: `looks.paint(cv, 'swirl', scene, t)`; `the sky eddies sit beside the sun: give the scene a sun to turn them round`. Example: `examples/capabilities/look-swirl.py`.
- **Pointillism** (`pointillism`): Ten thousand dots of colour that shimmer. Ask: "Paint it all in tiny dots". Build: `looks.paint(cv, 'pointillism', scene, t)`; `scene.role_at(x, y) colours each dot by its region`. Example: `examples/capabilities/look-pointillism.py`.
- **Ukiyo-e woodblock** (`woodblock`): Flat colour, thick ink lines, and a great wave that curls. Ask: "Make it look like an old Japanese woodblock print". Build: `looks.paint(cv, 'woodblock', scene, t)`; `the wave curls on age: pass the seconds since the look came on`. Example: `examples/capabilities/look-woodblock.py`.
- **Surrealist melt** (`melt`): A dream: the clock melts, the tower sways like wax. Ask: "Make it surreal, like a dream where things melt". Build: `looks.paint(cv, 'melt', scene, t)`; `scene.ledge() is where the clock drapes: give the scene some land`. Example: `examples/capabilities/look-melt.py`.
- **Bauhaus geometry** (`bauhaus`): Primary colours and simple shapes that turn on the beat. Ask: "Make it geometric, all circles and primary colours". Build: `looks.paint(cv, 'bauhaus', scene, t)`; `Scene(bpm=...) sets the beat the shapes pulse on`. Example: `examples/capabilities/look-bauhaus.py`.
- **Pop-art halftone** (`pop-art`): Loud flat colour, comic dots, and a burst that pops. Ask: "Make it pop art, comic-book dots and bold colours". Build: `looks.paint(cv, 'pop-art', scene, t)`; `looks.paint(cv, 'pop-art', scene, t, sfx='POW!', font=vb.Font(...))  # the burst's word`. Example: `examples/capabilities/look-pop-art.py`.
- **8-bit pixel** (`pixel`): Blocky pixels, everything moving in little steps. Ask: "Make it look like an old 8-bit video game". Build: `looks.paint(cv, 'pixel', scene, t)`; `looks.paint(cv, 'pixel', scene, t, block=16)  # bigger pixels`. Example: `examples/capabilities/look-pixel.py`.
- **Blueprint** (`blueprint`): Chalk lines that draw the scene in on a blue grid. Ask: "Make it look like a blueprint that draws itself". Build: `looks.paint(cv, 'blueprint', scene, t)`; `looks.paint(cv, 'blueprint', scene, t, age, font=vb.Font(...))  # labels on the dimension line`. Example: `examples/capabilities/look-blueprint.py`.
- **Paper collage** (`paper-collage`): Torn-paper headlines, cut-paper objects, a stamp, and a rip-open transition. Ask: "Make this look like a paper collage explainer, all torn paper and cut-outs". Build: `paths.torn(outline, seed, amount=5)  # a torn edge, baked once at import`; `cv.shape_shadow(points, dx=.., dy=.., blur=..)  # a lift shadow that follows the shape`; `vb.paper_grain(w, h, seed)  # with cairo.OPERATOR_SOFT_LIGHT`; `stepped_n = n - n % 2  # paper held on twos`. Example: `examples/capabilities/paper-collage.py`.

*Filter looks*, for any picture: a photo, a screen capture, footage, every pixel restyled:

- **Pop-art filter** (`pop-art`): Any picture in loud flat colour, comic dots and thick outlines. Ask: "Make my product demo pop art". Build: `with looks.filter(cv, 'pop-art', t): draw_as_usual(n, cv)`; `videobuilder.halftone_pattern(pitch, radius, angle=.., color=..)  # a hand-drawn dot fill`; `cv.arc(..., width=..)  # the thick outline`; `videobuilder/looks/popart.py  # dot fills, outlines and the starburst, worked`. Example: `examples/capabilities/look-filter-pop-art.py`.
- **8-bit pixel filter** (`pixel`): Any picture as chunky 8-bit pixels, stepped like an old game. Ask: "Make my product demo look like an old 8-bit video game". Build: `with looks.filter(cv, 'pixel', t): draw_as_usual(n, cv)`; `looks.get_filter('pixel').step(t)  # draw the picture at this time to step with the filter`; `cv.pixelated(factor)  # one blocky layer of a drawn scene; draw with the canvas it yields`; `stepped_n = (n // 2) * 2  # 15fps motion on a 30fps film`. Example: `examples/capabilities/look-filter-pixel.py`.
- **Woodblock filter** (`woodblock`): Any picture as a woodblock print, its paper boiling on twos. Ask: "Make this photo look like an old Japanese woodblock print". Build: `with looks.filter(cv, 'woodblock', t): draw_as_usual(n, cv)`. Example: `examples/capabilities/look-filter-woodblock.py`.
- **Blueprint filter** (`blueprint`): Any picture as chalk lines on a blue grid, a scan line sweeping. Ask: "Turn the product screenshots into a blueprint". Build: `with looks.filter(cv, 'blueprint', t): draw_as_usual(n, cv)`. Example: `examples/capabilities/look-filter-blueprint.py`.
- **Pointillism filter** (`pointillism`): Any picture rebuilt from shimmering dots of its own colours. Ask: "Paint this photo in tiny dots". Build: `with looks.filter(cv, 'pointillism', t): draw_as_usual(n, cv)`. Example: `examples/capabilities/look-filter-pointillism.py`.

Old ids, now part of these: `comic-halftone` is the **Pop-art filter**; `pixel-art-layer` is the **8-bit pixel filter**.

## Type

### Type

**What it looks like:** Named typography styles any video can ask for by name, every one taking the same few props. Type-only moments asked for by name ("make the title a split-flap board", "type it on like a terminal", "make the letters bounce"): each style is a short typography film of its own -- the letters enter, hold while still moving, and leave -- drawn from the same props every style takes: one to four short lines, three colours (ink, paper, accent) and a length, 6 s inside a film or up to 18 s as a film of its own. Each lays itself out for tall, wide and square frames, can run in a box or over another picture, and the ones with an obvious sound (flap clicks, key strikes, a soft pop) bring it when asked.

**When to use it:** reach for this when a director says something like:
- "Make the title a split-flap departures board"
- "Type the headline on like a terminal, with a prompt"
- "Make the slogan bounce in, letters on springs"
- "Show me the same title in a few type styles"

**How to build it:**
- `TITLE = vb.type.props(lines=['Gate 14', 'Now boarding'], ink=, paper=, accent=, length=6)`
- `vb.type.draw(cv, 'split-flap', TITLE, t)  # t: seconds since the style started`
- `vb.type.draw(cv, 'rubber', vb.type.props(TITLE, paper=None), t, box=(x, y, w, h))  # over a picture`
- `vb.type.film('typewriter', TITLE, length=18)  # one style as a film of its own`
- `vb.type.sounds(name, vb.type.props(TITLE, sound=True), at=frame)  # its clicks, keys or pops`
- `vb.type.props(TITLE, texture=False)  # a plain ground: no paper grain or scanlines`
- `vb.type.names() / vb.type.get(name)`
- `vb.type.relay(cv, names, TITLE, t, each=3.0)`
- `vb.type.motion_floor(film, start, end) >= vb.type.FLOOR`
- Read `skill/make-a-video/reference/type.md`.

**Worked example:** `examples/capabilities/type.py` — read it before writing something similar from scratch.

**The type styles** (7; ask for any type style by name):

- **Split-flap board** (`split-flap`): A departures board: every letter flips through the alphabet and settles. Ask: "Make the title a split-flap departures board". Build: `vb.type.draw(cv, 'split-flap', props, t)`. Example: `examples/capabilities/type-split-flap.py`.
- **Typewriter** (`typewriter`): Letters strike in one at a time, a little uneven, the caret riding the line. Ask: "Type the quote out like an old typewriter". Build: `vb.type.draw(cv, 'typewriter', props, t)`. Example: `examples/capabilities/type-typewriter.py`.
- **Terminal** (`terminal`): Typed at a prompt with a block cursor, then deleted back to the prompt. Ask: "Type the headline in like a terminal command". Build: `vb.type.draw(cv, 'terminal', props, t)`. Example: `examples/capabilities/type-terminal.py`.
- **Rubber letters** (`rubber`): Bouncy letters that squash, stretch and settle on springs. Ask: "Make the slogan bounce in, letters on springs". Build: `vb.type.draw(cv, 'rubber', props, t)`. Example: `examples/capabilities/type-rubber.py`.
- **Rack focus** (`rack-focus`): Lines pull out of a soft haze into focus, one after another. Ask: "Bring the lines into focus one at a time". Build: `vb.type.draw(cv, 'rack-focus', props, t)`. Example: `examples/capabilities/type-rack-focus.py`.
- **Letter cloud** (`letter-cloud`): Letters scattered in 3D fly together into the words. Ask: "Have the letters fly together out of a 3D cloud". Build: `vb.type.draw(cv, 'letter-cloud', props, t)`. Example: `examples/capabilities/type-letter-cloud.py`.
- **Editorial stack** (`editorial`): Stacked capitals revealed by hard wipes in the accent, magazine style. Ask: "Make the headline a magazine cover, big stacked type". Build: `vb.type.draw(cv, 'editorial', props, t)`. Example: `examples/capabilities/type-editorial.py`.

## Timing, sound and formats

### Cuts locked to the music

**What it looks like:** Hard cuts land exactly on the beat, with a music bed. A music bed drives the cut points directly: every segment starts on a beat of the grid, so the hard cuts land on the music instead of merely sitting near it.

**When to use it:** reach for this when a director says something like:
- "Cut this on the beat, with a music bed under it"
- "Lock the hard cuts to the grid, 120 bpm"
- "Add a placeholder music bed and cut to it"

**How to build it:**
- `vb.Audio(path, gain_db=..., fade_out_frames=...)`
- `skill's make_track.py synth(bpm, beats, ...)`
- `Segment starts are beats, so cuts are on-grid by construction`
- Read `skill/make-a-video/reference/music.md`.

**Worked example:** `examples/capabilities/beat-lock.py` — read it before writing something similar from scratch.

### Footage with its own sound

**What it looks like:** A clip plays with its sound while the music dips under it. A speaker clip cuts in and plays with its own sound, mixed with the music bed: the music dips under the speech while the clip plays and comes back up when it ends, and the whole mix is evened out to one loudness, so the voice is easy to hear without the music ever cutting out.

**When to use it:** reach for this when a director says something like:
- "Use this clip with its sound, and bring the music down under the speech"
- "Let us hear the speaker, then bring the music back up after"
- "Cut between the interview clips and the graphics, with the music underneath"

**How to build it:**
- `vb.Sound(path, at=, start=, frames=, fade_in_frames=, fade_out_frames=)`
- `ft = vb.footage(TIMELINE, 'segment', start=seconds)  # picture and sound in sync`
- `clip.frame(clip.frame_at(ft.seconds_at(n)))`
- `ft.sound(path) -> Film(sounds=(...))`
- `vb.Audio(music, duck_db=-8)  # the music ducks while a sound plays; -8 for music under a voice-over, ramps and short-gap bridging are automatic`
- Read `skill/make-a-video/reference/footage.md`.

**Worked example:** `examples/capabilities/footage-with-sound.py` — read it before writing something similar from scratch.

### Narration

**What it looks like:** A generated voiceover, captioned, with a character that talks. A voiceover read from a short script by a text-to-speech voice (Kokoro, open weights), made once and kept with the video like any other sound file: the captions follow it phrase by phrase, and a cut-out character's mouth opens and shuts with the voice. To ask for it, give the words to say, one phrase or sentence per line, and the kind of voice (a calm American woman, a British man...). If a name comes out wrong, say how it should sound ("Galgs rhymes with dolls") and the builder respells it for the voice while the captions keep the real spelling. The voice reads the words as written; it does not act them.

**When to use it:** reach for this when a director says something like:
- "Add a voiceover that says this script, with captions under it"
- "Use a calm British voice, a little slower"
- "Make the fox say this line, mouth moving with the words"
- "It says our product name wrong: it should sound like "loo-men""

**How to build it:**
- `python -m videobuilder say script.txt --out assets/voice.wav [--voice af_heart] [--speed 1.0]  # once; commit the .wav, .vtt, .json and the script`
- `[Lumen](/lˈuːmən/) in the script, or --say Lumen=Loomen  # fix a pronunciation; say --phonemes shows it`
- `VOICE = vb.speech.load('assets/voice.wav'); Film(sounds=(VOICE.sound(at=frame),))`
- `vb.captions.draw(cv, VOICE.track_at(frame, fps), n / fps)  # a cue per phrase`
- `mouth = VOICE.mouth(fps, at=frame, frames=TOTAL); pose = 'talk' if mouth[n] else 'idle'`
- Read `skill/make-a-video/reference/narration.md`.

**Worked example:** `examples/capabilities/narration.py` — read it before writing something similar from scratch.

### Sound effects

**What it looks like:** A whoosh, a click, a ding and a hit, each on its frame. Ready-made sound effects (whooshes, clicks and taps, pops, dings, risers, hits, sub drops, shimmers) put on the exact frame of the motion they sell: a whoosh peaks as a card whips past, a click lands on the press, a ding on the notification landing, a hit on the impact frame. They sit in the mix with the music and dip under a voice like it does. To ask for one, say what should make a sound and when ("a whoosh on the whip pan", "a click when the button is pressed"); a few well-placed sounds read better than one on every cut.

**When to use it:** reach for this when a director says something like:
- "Add a whoosh when the card flies in"
- "Put a click on each button press"
- "Make the logo land with a hit"
- "Add a soft ding when the notification appears"

**How to build it:**
- `vb.sfx.sound('whoosh_fast/tight', at=frame, dur=0.5, gain_db=-8)  # its peak on the frame`
- `vb.sfx.sound('fit/click/floss_lid', at=frame, align='onset')`
- `vb.sfx.sound('pro_notify/ding_2045', at=frame, note='G5')  # a tuned sound by note`
- `vb.sfx.find('whoosh', near_dur=0.8)  # by role`
- `Film(sounds=(...))`
- `{"sfx": "pro_impact/short", "at": 120} in a timeline.json lane; "sound": "auto" on a whip or flash`
- Read `skill/make-a-video/reference/sfx.md`.

**Worked example:** `examples/capabilities/sound-effects.py` — read it before writing something similar from scratch.

### Every format, recomposed

**What it looks like:** One scene, laid out separately for three shapes. The same scene laid out three separate ways — 9:16, 16:9 and 1:1 — each from its own per-format layout table, not one layout cropped three ways.

**When to use it:** reach for this when a director says something like:
- "Lay this out for 9:16, 16:9 and 1:1, not just one format"
- "Recompose this for square, not just crop it"
- "Give portrait its own layout table, not a cropped landscape one"

**How to build it:**
- `per_format(LAYOUTS, cv)`
- `one LAYOUTS entry per vb.Format, each computed from that format's own geometry`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/every-format.py` — read it before writing something similar from scratch.

### Seamless loops

**What it looks like:** A clip built to play forever with no visible seam. A continuously looping shot, its motion driven by a repeating cycle, so the state at the last frame and the state at frame 0 are mathematically the same point in the cycle, not just visually close.

**When to use it:** reach for this when a director says something like:
- "Make this loop seamlessly"
- "This needs to play on repeat with no jump at the seam"
- "Drive the motion in a cycle that wraps around cleanly, with no jump at the seam"

**How to build it:**
- `phase = (n % length) / length`
- `vb.linear for phase/rotation`
- `LOOP = True  # tells check.py to grade the seam`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/seamless-loops.py` — read it before writing something similar from scratch.

## Capability families

Hundreds more capabilities (easing curves, transitions, text reveals and the like), too many to list here one by one: each lives in its own file under `videobuilder/capabilities/<family>/<id with - as _>.py`, ending in a module-level `CAPABILITY = Capability(...)` (see `videobuilder/capabilities/schema.py`), with a short demo of its own. List a family's with `python -m videobuilder capabilities index --family <family>` (drop `--family` for every one; add `--json` for machine-readable output). Call what its `api` names to use one in a film -- some are videobuilder's own functions, the rest live in the module itself and are imported from there; its own `draw` is a worked demo of the capability alone, read before using it the first time. Add a new one the same way, one new file and nothing else edited, checked by `python3 -m unittest tests.test_capabilities_registry.EachCapability.test_<id with - as _>`. The families:

- **Animation principles** (`principles`): The animator's classic toolkit: easing, timing and weight.
- **Typography** (`typography`): Type-only moves: reveals, effects and kinetic lettering.
- **Transitions** (`transitions`): Ways from one shot to the next.
- **UI and interaction** (`ui`): Interface moves: buttons, cursors, menus and loading states.
- **Shapes and icons** (`shapes`): Vector shapes and icons that draw on, morph and move.
- **Particles and generative** (`particles`): Particle systems and seeded generative motion.
- **Camera moves** (`camera`): Virtual camera moves: pans, zooms, shakes and racks.
- **Visual effects** (`vfx`): Compositing-style effects: glows, distortions and glitches.
- **Broadcast graphics** (`broadcast`): TV-style graphics: lower thirds, tickers and scoreboards.
- **Sound** (`sound`): Sound-only capabilities: foley, stingers and audio cues.


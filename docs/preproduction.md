# Pre-production

A video's director can ask the builder to **develop a film before any of it
gets built**: a script, characters with pictures, a look, and a plan of
scenes -- with real choices to pick from, not a finished cut. This is
**pre-production**. A video starts in it when the director asks for that
(see "New video" below); it can also be turned on, or back off, at any
time from the video's own board. Nothing renders in pre-production, not
even on request -- stills are fine, a full render is not -- and the
director can **start production** whenever the plan is good enough, even
with some of it still open: the builder decides anything left open itself
and says what it decided.

Everything below is written for whoever builds the board page, the New
video page, and the chat pass that shows picture option cards -- it is the
complete API and file reference; nothing else is needed to build them.

The examples throughout use an invented film about a lighthouse keeper
riding out a storm -- nothing here comes from a real project.

## The checklist

The board shows a simple checklist, "N of 5 settled" -- derived from the
files below each time it is asked for, never stored on its own:

| id | label | settled when |
|---|---|---|
| `logline` | Logline | `bible.md`'s `## Logline` section is non-empty |
| `script` | Script draft | `bible/script.fountain` exists and has at least one scene heading |
| `look` | Look | the `look` option set has a pick; or, with no `look` set, `bible.md`'s `## Look` is non-empty |
| `cast` | Cast | there is at least one character, and every `character-<slug>` set has a pick |
| `scenes` | Scene plan | there is at least one scene, and every `scene-<id>` set has a pick |

Each item is `{id, label, settled, detail}`; `detail` is `{text}` for
`logline`, `{draft, scenes}` for `script`, `{label}` for `look`,
`{picked: [name...], open: [name...]}` for `cast`, and
`{count, seconds, open: [scene id...]}` for `scenes`.

## The bible, in pre-production

Everything pre-production holds lives under `bible/`, beside Film details'
own `bible.md` and `bible/characters/`. All of it is plain files in the
video's own git repo -- the builder writes and revises them like any other
file, and the director edits them through the API below, each edit landing
as an ordinary commit.

```
bible/phase.json          the video's phase
bible/script.fountain     the screenplay, in Fountain
bible/scenes.json         scene cards: songs and scenes
bible/options/<id>.json   one option set
bible/options/<id>/       that set's pictures, named <key>.<ext>
```

### `bible/phase.json`

```json
{"phase": "pre-production"}
```

`phase` is `"pre-production"` or `"production"`. A video with no such file,
or one that doesn't parse, is in `"production"` -- an existing video needs
no migration. Flipping it back to pre-production later changes nothing
else; flipping it to production sends the builder a note (see "Start
production" below).

### `bible/script.fountain`

The screenplay, in [Fountain](https://fountain.io), the plain-text
screenplay format: scene headings, action, character names, dialogue,
parentheticals, transitions, sections and synopses, told apart by
Fountain's own plain-text conventions (`INT.`/`EXT.` or a leading `.` for a
heading, `ALL CAPS` for a character cue, a leading `>` for a transition, a
leading `#` for a section, a leading `=` for a synopsis). A title page's
`Draft: N` field is the draft number; raise it on a real rewrite, not a
line edit. A scene heading may end in `#n#` to fix its number explicitly;
without one, a scene is numbered by its position among headings.

```
Title: The Keeper's Light
Draft: 2

INT. LIGHTHOUSE - LANTERN ROOM - NIGHT #1#

The lamp turns. Rain needles the glass.

MARA
(checking the log)
Still turning. Good.

> CUT TO:

EXT. LIGHTHOUSE - CLIFF - NIGHT #2#

The sea throws itself at the rock.
```

**Line comments.** The director comments on a line through the ordinary
notes API (`POST /api/notes`), quoting it in the note's text so the builder
knows exactly which line:

```
Script, draft 2, scene 1, line 7: "Still turning. Good."
Can she sound more rattled here -- she just saw something in the water.
```

### `bible/scenes.json`

Scene cards: one per planned scene, plus the songs they can sit on.

```json
{
  "songs": [
    {"id": "storm-theme", "name": "Storm theme", "file": "storm-theme.mp3",
     "duration": 142.5, "bpm": 92, "mood": "tense, building",
     "sections": [{"name": "intro", "start": 0, "end": 18, "text": "sparse, just wind"}]}
  ],
  "scenes": [
    {"id": "lantern-room", "slugline": "INT. LIGHTHOUSE - LANTERN ROOM - NIGHT",
     "summary": "Mara checks the lamp as the storm builds.", "seconds": 28,
     "song": "storm-theme", "section": "intro", "from": 0, "to": 18,
     "look": {"name": "Moody", "reason": "small, warm light against a huge dark sea"}}
  ]
}
```

A scene's `id` follows the same shape a timeline clip id does
(`^[a-z0-9][a-z0-9-]{0,79}$`) **on purpose**: when production starts, each
scene becomes a planned (or built) clip with that same id, so the scene
plan and the film of clips line up one to one. `song` names a song's `id`;
`section`/`from`/`to` (seconds, `to` greater than `from`) say where on that
song the scene sits -- `section` needs a `from`, needs a `song`. A scene's
position in the list is its number; reordering the list renumbers them.
`look`, when given, is a plain note on this scene's own look, not a set.

The board's GET adds, per scene, `number` (1-based), `length` and
`from_clock`/`to_clock` (each `m:ss`, from `clock()`: `seconds // 60` and
`seconds % 60`, floored to the second), and `set` (the id of this scene's
plot-alternatives set, if it has one, else null).

### `bible/options/<id>.json`

One **option set**: 2-4 choices for one decision, with a pick.

```json
{
  "id": "look",
  "topic": "look",
  "question": "Which look fits the storm best?",
  "pick": "A",
  "options": [
    {"key": "A", "label": "Moody", "text": "Low-key lighting, long shadows, a single warm light.",
     "image": "bible/options/look/A.png", "kind": "vb",
     "swatches": ["#101418", "#5a4632", "#8aa0b0"]},
    {"key": "B", "label": "Bright", "text": "High-key, saturated colour, storm as spectacle.",
     "image": null, "kind": null}
  ]
}
```

- `topic` is `"look"`, `"character"`, `"scene"`, or `"other"`, and fixes the
  set's `id`: always `"look"` for the look; `"character-<slug>"` for a
  character (`character` names the slug); `"scene-<scene id>"` for a
  scene's plot alternatives (`scene` names the scene id); for `"other"`,
  any id matching `[a-z0-9][a-z0-9-]{0,59}`.
- `options` is 2-4 entries, each with a unique `key` (one of `A`-`D`), a
  `label` (≤80 characters), `text` (≤400 characters), and either both
  `image`/`kind` or neither. `image` is a path under `bible/` to a picture
  in a known extension (png/jpg/jpeg/webp/gif), with no `..` segment.
  `kind` is one of:
  - `vb` -- a real frame, rendered with videobuilder; what production can
    actually draw.
  - `concept` -- image-generator art: "concept art, not final".
  - `yours` -- the director's own uploaded picture.
  A look option may also carry up to 5 `swatches`, each `#rrggbb`.
- `pick` is one of the options' keys, or null.

`bible/options/<id>/<key>.<ext>` holds that option's picture, alongside
the set's JSON file.

## Concept art

A `concept`-kind picture is generated for the builder, not by it: the
builder asks for one (see "The concepts block" below), and the editor
makes it through artbox (a home GPU, no per-image cost) once the note that
asked lands. Each request tracks a `status`:

| status | meaning |
|---|---|
| `requested` | accepted; waiting to see whether the note that asked actually lands |
| `making` | submitted to artbox, being generated |
| `done` | committed into the bible (the option's `image`/`kind` now point at it) |
| `unavailable` | won't happen; `message` says why: no artbox configured on this editor, artbox isn't answering, the image failed, the builder's change wasn't kept, or the request was over the note's own cap |

A note's own `concepts` field (see below) lists its requests and their
current status; a reply still shows at once even while they are still
being made (or if artbox is down) -- the picture, or the "unavailable"
notice, fills in once it's known.

## Chat: picture choices and picks

A builder reply may end with a ```` ```questions ```` fenced block (as
always); a choice may now be a plain string (free text, unchanged) or an
object:

```` ```questions
{"questions": [{"text": "Which look fits best?", "set": "look", "choices": [
  {"text": "Moody, low-key lighting", "image": "bible/options/look/A.png", "kind": "vb", "key": "A"},
  {"text": "Bright and saturated", "image": "bible/options/look/B.png", "kind": "concept", "key": "B"}
]}]}
```` ````

A question's `choices` always stays a list of plain strings, so a chip
renderer that knows nothing about pictures keeps working exactly as
before. When any choice was an object, the question also gets `options`:
`[{text, image, kind, key}|null, ...]`, aligned with `choices` (null where
a choice was a plain string); when the block named one, the question also
gets `set` (the option-set id a pick here should record against). An
image choice needs a `kind`; the image must be a `bible/` picture path, no
`..`, a known extension. Answering with text equal to one option's own
`text` records that option's pick, exactly like clicking it on the board.

### The concepts block

To ask the editor to generate concept art, a reply ends with a separate
fenced block instead of (or alongside) a questions block:

```` ```concepts
{"concepts": [{"set": "look", "key": "C", "prompt": "a moody lighthouse lantern room, rain on the glass"}]}
```` ````

The target picture is always `bible/options/<set>/<key>.png`, so the
builder can reference it in the set file before it exists. At most 3
requests per `character-*` set, 4 for `look`, 4 for any other set, and 16
per note in total; anything past that is simply marked `unavailable`
("over the limit for one note"). The block is stripped from the reply
before it's shown, and only looked for at all on a pre-production note --
a production reply's text is never scanned for one and so is byte-for-byte
unaffected by this feature existing.

### Note fields

A note submitted while its video is in pre-production carries:

- `phase`: `"pre-production"`.
- `picks` (only when non-empty): every option pick (or clear) recorded
  since this video's last submitted note, `[{set, key, label, author, at}]`
  -- `key` is null for a clear. The builder's prompt lists these under
  "## Picks since your last note"; a note submitted with none carries no
  such section. This one is not limited to pre-production: Start
  production's note (or any later one) carries the picks made just before
  it.
- `concepts` (only when the reply asked for any): `[{set, key, prompt,
  status, message}]`, each request with its current `status` (and
  `message` once `unavailable`), current whenever the note is read.

A note submitted in production, with no picks pending, is byte-for-byte
the same as before pre-production existed.

## Endpoints

Per-video (single project: `/api/...`; library: `/v/<name>/api/...`).

### `GET /api/preprod?video=V`

```json
{"commit": "<sha>", "phase": "pre-production",
 "logline": "...", "look": {"text": "...", "set": "look"|null},
 "script": {"exists": true, "draft": 2, "title": "The Keeper's Light", "scenes": 6},
 "characters": [{"slug": "mara", "name": "Mara", "description": "...", "pictures": ["mara-1.png"], "set": "character-mara"|null}],
 "sets": [ /* every bible/options/<id>.json, as stored */ ],
 "scenes": {"songs": [...], "scenes": [ /* each with number, length, from_clock, to_clock, set, see above */ ], "seconds": 420, "length": "7:00"},
 "checklist": [ /* the 5 items above */ ],
 "concepts": [{"set": "look", "key": "C", "image": "bible/options/look/C.png", "status": "making", "message": null, "note": "<note id>"}],
 "problems": [{"file": "bible/options/look.json", "error": "..."}]}
```

404 for an unknown video. A malformed bible file (one that doesn't parse,
or a hand-edited file that no longer validates) is never a 500: it is
skipped and listed in `problems` instead, and everything else on the
board still shows. `concepts` is every concept-art request made on this
video's notes, one per slot (the newest note's request wins when a slot was
asked for more than once), with the picture's path and its current status
-- the same status as the asking note's own `concepts` field.

### `GET /api/preprod/script?video=V[&draft=N]`

```json
{"commit": "<sha>", "text": "...", "title": "The Keeper's Light", "draft": 2,
 "scenes": [{"number": 1, "heading": "INT. LIGHTHOUSE - LANTERN ROOM - NIGHT", "line": 4}],
 "elements": [{"type": "heading", "text": "...", "line": 4, "scene": 1}],
 "drafts": [{"n": 2, "commit": "<sha>", "time": "2026-01-01T00:00:00Z"}, {"n": 1, "commit": "<sha>", "time": "..."}]}
```

`type` is one of `heading`, `action`, `character`, `dialogue`,
`parenthetical`, `transition`, `section`, `synopsis`. `drafts` is the
newest commit for each distinct draft number seen in the file's last 50
commits, newest draft first. With `draft=N`, the text (and `commit`) come
from that draft's commit instead of the working tree. 404 when there is no
script yet, or no such draft.

### `GET /api/preprod/image?video=V&path=P`

The picture's raw bytes, `Content-Type` from its extension,
`Cache-Control: private, max-age=60`. 404 unless `P` is a `bible/` picture
path with no `..` and the file actually exists there.

### `POST /api/preprod/script {video, base, text}`

Commits `bible/script.fountain` (`text`, a string of at most 200,000
characters). 200: the script GET body (at the new commit) plus `changed`
(false if nothing actually changed) and `n` (the version number). 400 for
a bad `text`. 409 when the script changed on main since `base` (the commit
the editor was opened at) -- reload and retry.

### `POST /api/preprod/scenes {video, base, songs, scenes}`

Replaces `bible/scenes.json` whole (reorder by sending the new order). 200:
the board body (`GET /api/preprod`'s shape) plus `changed`, `n`. 400 for
anything invalid: a bad scene or song id, duplicate ids, `to` not greater
than `from`, a scene naming an unknown song. 409 stale `base`.

### `POST /api/preprod/sets {video, base, set}`

Creates or replaces one option set (`set` is the JSON shown above). An
option may carry `upload: "<attachment id>"` instead of (or alongside) an
`image`/`kind` -- an attachment already on this video, not an SVG -- which
is copied in as `bible/options/<id>/<key>.<ext>`, kind `"yours"`. 200: the
board body plus `changed`, `n`. 400 invalid (wrong id for the topic, too
few/many options, duplicate keys, a bad image path, an image with no kind,
an SVG upload, an unknown upload id). 409 stale `base`.

### `POST /api/preprod/sets/delete {video, base, id}`

Removes the set's file and its whole picture folder. 200: the board body
plus `changed`, `n`. 404 for no such set.

### `POST /api/preprod/pick {video, set, key}`

Records (or, with `key: null`, clears) a pick -- the same effect clicking
an option on the board has, committed as `Pick: <set> <key|cleared>` and
queued for the builder's next prompt. 200: the board body plus `changed`,
`n`. 404 for no such set; 400 for a key that isn't one of the set's own.
No `base`: a pick only names a key, checked against the set as it stands
on main right now.

### `POST /api/phase {video, phase}`

Flips the phase. 200 `{phase, changed, commit, n, note}`. Switching to
`"pre-production"` only writes `bible/phase.json` -- `changed: false` and
no new commit if it was already there. Switching to `"production"` first
checks the note cap (429, as `POST /api/notes`) and that the video loads
(409 "the video does not load; fix it before starting production"), then
writes the file and sends the builder a `no_questions` note naming the
bible, the script and the scene plan and listing anything on the
checklist still open, asking the builder to decide those itself and say
what it decided in its reply (`note.said == "Start production"`); `note`
is null when nothing changed. 400 for a `phase` that isn't one of the two
values.

### Render routes in pre-production

`GET /api/video`, `GET /api/clip` and `POST /api/video/retry` all answer
**409** `{"error": "This video is in pre-production: nothing renders
until production starts."}` while the video is in pre-production, even
when a render is asked for explicitly. Stills (`GET /api/frame`, draft
previews, thumbnails) are unaffected -- they aren't renders.

## New video

New video is where a director starts a brand-new project, with the choice
of planning it first or building straight away, decided for them with a
one-line reason they can flip before they commit to it.

### `POST /api/videos/staging?name=F`

Library-only, never reachable with an API key. The raw file as the body,
`Content-Type` set -- exactly like `POST /api/attachments`, except there
is no video yet to attach to. Called as each file is dropped or picked on
the New video page, before Start is clicked, so the page can show upload
progress per file. 201 `{id, name, type, size}`. 400 for an unrecognised
type, a magic-bytes mismatch, or a `.zip` (unpack it and add its files
instead). 413 for a file over 25 MiB, or once the signed-in owner (or,
with no accounts, the shared anonymous pool) already has 50 staged files
or 300 MiB staged. Starting to listen to an audio file begins right away
(see "Listening early" below). An unclaimed file is removed after 24
hours.

### `POST /api/videos/staging/<id>/delete {}`

Removes a staged file before it's used. 200 `{deleted: id}`. 404 for an
unknown id, or one staged by someone else.

### `POST /api/videos/mode {prompt?, types?: [mime, ...]}`

The plan-or-build suggestion for a prompt and the MIME types of whatever
has been staged so far -- callable as the director types or drops files,
before anything is created, so the page can show (and let them override)
the suggestion ahead of Start. 200 `{plan, why, reason}`. `why`, in the
order it's decided:

1. `"story"` -- the prompt reads like a story: it uses, as a whole word,
   one of screenplay, script, scene(s), character(s), story/stories, plot,
   backstory, logline, protagonist, dialogue, chapter(s), episode(s),
   narrative; or it's at least 80 words long either way.
2. `"references"` -- no story words, but at least one staged file is an
   image or a PDF or text document.
3. `"media-only"` -- no words in the prompt at all, and every staged file
   is video or audio.
4. `"short-idea"` -- some other non-empty prompt, no references.
5. `"empty"` -- nothing at all yet.

`plan` is true for `"story"` and `"references"`, false otherwise. `reason`
is a fixed one-line explanation for that `why`.

### `POST /api/videos/new`

```json
{"name": "acme/launch", "start": "blank",
 "prompt": "Develop a multi-scene screenplay for a lighthouse keeper riding out a storm.",
 "attachments": ["<staged id>", "..."], "format": "9x16", "plan": true}
```

`prompt`, `attachments`, `format` and `plan` apply only to `start:
"blank"` -- any of them with `start: "copy"` is 400. All are optional.
`format`, when given, is one of videobuilder's formats (`9x16`, `16x9`,
`1x1`); the blank film is narrowed to it, instead of today's `9x16`+`16x9`
pair, and the first note says so (`Format: 9x16.`). `attachments` are ids
from `POST /api/videos/staging`; they are copied in as the new video's own
attachments (and the staged entries removed) once the first note actually
goes out.

With `plan` omitted, the same rule `POST /api/videos/mode` answers decides
it (`why` is one of the five values above); given explicitly, `why` is
`"chosen"` and `reason` says the director chose it ("You chose to plan it
first." / "You chose to build it straight away.").

With `plan: true`, the video is created already in pre-production
(`bible/phase.json`) and, if there is a `prompt` or any `attachments`, the
first note asks the builder to develop the film with the director --
script, characters, look and a scene plan, with real options -- rather
than build anything yet. With `plan: false` or omitted-and-decided-false,
the first note is today's "Build a first version..." brief. With neither a
`prompt` nor any `attachments` at all, no first note is sent regardless of
`plan` -- the video is simply created, in whichever phase.

201:

```json
{"name": "acme/launch", "commit": "<sha>", "video": "film",
 "plan": true, "why": "story", "reason": "...",
 "note": { /* ...the note, or null */ }, "note_error": null,
 "attachments": [{"id": "...", "name": "...", "type": "...", "size": 123}]}
```

`video` is the sole video's id for `"blank"` (always `"film"`), null for
`"copy"`; for `"copy"`, `plan`/`why`/`reason`/`note`/`note_error` are null
and `attachments` is `[]` -- copying a video never plans or sends a note.
`note` is null when none was sent; it is also null, with `note_error` set
to why, if the video was created but the first note itself then failed
(for instance, the video somehow doesn't load) -- the video still exists
and can be sent a first note the ordinary way
(`POST .../api/videos/first-note`), and anything staged for it is left in
place rather than silently lost.

Everything is validated -- the name, every staged attachment id, `format`,
`plan`'s type, and (for `"blank"`) the note cap -- **before** anything is
created: a 400 or 429 here always leaves no repository behind. 400 for an
invalid or already-taken name, an unknown staged attachment id, more
attachments than the first-note allowance (50 files / 300 MiB), an unknown
`format`, or a non-boolean `plan`. 429 as `POST /api/notes`, before the
video exists.

### `POST /api/videos/suggest-name {idea?, attachments?: [staged id, ...]}`

Library-only. The New video page's Suggest button on the Name field: a
short name guessed from `idea` and the names of whatever `attachments`
(staged ids, as above) are given, using the same suggestion model
`POST /api/suggest` does (configured by `--suggest-url`; see suggest.py).
For a staged audio file, when the listening cache (see "Listening early"
below) already has notes for it, those notes are read too -- not asked
for fresh. 200 `{name}`: a short string, or `null` when there is nothing
to go on yet, no model is configured, or the call itself failed (never an
error -- this must never break the page). `name` is a plain suggestion,
not validated as a real video name; the page runs it through the same
name validation any typed name gets before filling the field in. 404
without a model configured, so the page hides the button entirely.

### Listening early

As soon as an audio file is staged (`POST /api/videos/staging`) or
attached to an existing video (`POST /api/attachments`), the editor starts
listening to it in the background (with `$GEMINI_API_KEY` configured; a
no-op otherwise) -- so by the time a note actually needs those notes, they
are usually already cached, and the note doesn't wait on Gemini itself. A
note that does need to listen to the very same audio while an early listen
for it is still in flight waits for that one call to finish rather than
asking a second time.

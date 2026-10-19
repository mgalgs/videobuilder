"""A film made of clips: the timeline file, `timeline.json` at the video's root.

(Not `videobuilder.timeline`, which is the beat timeline inside one film.)

A video with a timeline file is an *assembly*: each clip is built and rendered
on its own, and the video is those renders cut together, plus Audio lanes. The
file holds only what a person changes directly on a film -- clip order, trims,
transitions, J/L cuts, Audio lanes and their items -- and nothing that belongs
in a clip's code. Everything else is a note to a builder.

Every time in the file is a whole number of frames at the file's `fps`.

    {
      "version": 1,
      "fps": 30,
      "formats": ["16x9", "9x16"],
      "clips": [
        {"id": "opening", "dir": "clips/01-opening"},
        {"id": "boat", "footage": "sources/boat.mp4", "in": 30, "out": 120,
         "head": 0, "tail": 6,
         "cut": {"transition": "dissolve", "frames": 12},
         "sound": {"gain_db": -2, "early": 6, "dialogue": true}},
        {"id": "credits", "dir": "clips/03-credits",
         "cut": {"transition": "whip", "frames": 8, "sound": "auto"}}
      ],
      "acts": [{"title": "The river", "clips": ["opening", "boat"]}],
      "lanes": [
        {"duck": true, "items": [
          {"sound": "sources/theme.mp4", "at": 0, "offset": 0, "frames": 240, "gain_db": -3},
          {"sfx": "pro_impact/short", "at": 96, "gain_db": -6}]}
      ],
      "beats": {"lane": 1, "item": 1, "bpm": 120, "first": 12}
    }

Clips, in order. Each is either
  - a *clip directory* (`dir`), holding its own film file (`film`, default
    `film.py`), rendered on its own and cached by content (see `assembly`);
  - or a *footage clip* (`footage`), a source file cut from frame `in` to
    frame `out` (exclusive, counted from the file's start at `fps`): no code,
    no render; it is cut, scaled to cover the frame and centre-cropped at
    assembly.
`head`/`tail` trim frames off the clip's start and end; the trims either side
of a cut are the outgoing clip's `tail` and the incoming clip's `head`.
`cut` is the cut *into* this clip from the one before (so it moves with the
clip when clips are reordered): `transition` is one of `TRANSITIONS`, and
`frames` its length (0 for `cut`); `sound`, optional, a sound effect on the
cut (see Sound effects). A dissolve or wipe overlaps the two clips
by `frames`, so the film gets that much shorter, and so do a whip (a fast
slide with motion blur) and a flash (a short cut through white). `wipe` and
`whip` take a `direction` (left, right, up, down; default left): the way the
picture moves. The first clip has no cut into it.
`sound` is the clip's own sound: `gain_db`; `early` frames it starts before
the clip's picture (a J-cut) and `late` frames it runs on after it (an
L-cut), revealing sound from the trimmed head/tail (or, for footage, the
source beyond `in`/`out`), so a J/L cut needs trimmed material on that side;
`dialogue` marks it as speech for the lanes to duck under.

Acts: optional titles over runs of consecutive clips, in order.

Lanes: Audio lanes, shown as "Audio 1", "Audio 2"... by position (they have no
other name). Each has `items`, a sound placed at timeline frame `at`, playing
`frames` frames from `offset` frames into the file, with `gain_db` and
`fade_in`/`fade_out` frames; `duck` dips the lane by `duck_db` (default -12)
while clip sound that is speech plays: a clip directory's film's `Sound`s,
each over its own span (as one film's music ducks under them); a footage
clip's caption cues, when its source has a caption file beside it
(`sources/boat.vtt`); or all of a clip's sound, when marked `dialogue`.

Sound effects: a lane item may be a sound from the sound-effects pack
(`vb.sfx`) instead of a file: `sfx`, its id, with its peak (`align`:
"peak", the default, or "onset") on timeline frame `at`, at `gain_db`; a
take by `variant` ("0.8s", "C5") or `note`, and `frames`, optional, the
length nearest to which it takes (cut to it with a short fade when longer;
it plays whole without). It dips with its lane under speech unless
`through`. A cut's `sound` puts one on the cut (a hard cut's first frame, a
transition's middle): "auto" (a whoosh on a whip, a hit on a flash), an id,
or an object of the lane item's keys without `at`.

Paths are relative to the video's root, POSIX, inside it. Footage and big
sounds live in the video's `sources/` (uploaded to the editor, hardlinked into
every checkout and render worktree by `videobuilder.sources`, never committed);
a small committed file anywhere in the repo works too.

Beats: an optional beat grid, for a reel cut to a song. `lane` and `item`
(counted from 1, as "Audio 1, item 1") name the lane item playing the song;
`bpm` is its tempo, `first` the frame of its first beat counted from the
start of its file at `fps`, `bar` its beats to a bar (default 4). Beat k is
at `first + k * fps * 60 / bpm` frames into the file (rounded half up), so
on the timeline at `at - offset` plus that, for as long as the item plays
(`beat_grid`). A timeline with a grid is a reel: its cuts belong on beats,
and `offbeat` names the ones that aren't, as warnings, never as errors.
Where a cut is: a hard cut's first frame of the incoming clip; a transition's
middle (its first frame plus half its frames, rounded down).
"""
import difflib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

NAME = 'timeline.json'
VERSION = 1
TRANSITIONS = ('cut', 'dissolve', 'wipe', 'whip', 'flash')
# "sound": "auto" on a cut: (sound effect, its length in transitions, gain_db) by transition.
AUTO_SOUNDS = {'whip': ('whoosh_fast/tight', 2, -6.0), 'flash': ('pro_impact/short', None, -6.0)}
SFX_KEYS = ('sfx', 'variant', 'note', 'frames', 'align', 'gain_db', 'through')
_SFX_ID = re.compile(r'^[a-z0-9_]+(/[a-z0-9_.]+)+$')
# Reserved for later; named so a file using one gets "not available yet", not "unknown".
LATER_TRANSITIONS = ('match',)
WIPE_DIRECTIONS = ('left', 'right', 'up', 'down')
DIRECTED = ('wipe', 'whip')   # the transitions that take a direction
DEFAULT_DUCK_DB = -12.0
DEFAULT_FADE = 3
# Keys a builder may reach for that mean something else here.
HINTS = {
    'trim': 'trim with "head" and "tail", frames off each end',
    'start': 'a footage clip runs from "in" to "out"; a lane item starts at "at", "offset" frames into its file',
    'end': 'a footage clip runs from "in" to "out"; a lane item plays for "frames"',
    'duration': 'lengths are "frames"',
    'transition': 'a transition goes in "cut": {"transition": ..., "frames": ...}',
    'name': 'lanes have no names: they are Audio 1, Audio 2... by position',
    'music': 'sound goes in "lanes"',
}
_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')


class TimelineError(ValueError):
    """A timeline file that doesn't validate; `problems` lists every one found,
    each starting with where it is (`clips[2] "boat": cut.frames ...`)."""

    def __init__(self, source, problems):
        self.source, self.problems = source, list(problems)
        super().__init__(f'{source}: ' + ('\n  '.join([''] + self.problems) if len(self.problems) > 1
                                          else self.problems[0]))


@dataclass(frozen=True)
class SfxCue:
    """A sound effect from the pack (`vb.sfx`): its id (or 'auto', on a
    cut), the take (`variant`, or `note`, or the length nearest `frames`;
    0 plays the base take whole), what of it lands on its frame (`align`)
    and whether it dips under speech with its lane (not when `through`)."""
    sfx: str
    variant: str | None = None
    note: str | None = None
    frames: int = 0
    align: str = 'peak'
    gain_db: float = 0.0
    through: bool = False


@dataclass(frozen=True)
class Cut:
    """The cut into a clip from the one before it."""
    transition: str = 'cut'
    frames: int = 0
    direction: str = 'left'   # wipe and whip only
    sound: SfxCue | None = None


@dataclass(frozen=True)
class ClipSound:
    """A clip's own sound: gain, J/L overlap, and whether it is speech."""
    gain_db: float = 0.0
    early: int = 0     # J-cut: frames it starts before the clip's picture
    late: int = 0      # L-cut: frames it runs on after it
    dialogue: bool = False


@dataclass(frozen=True)
class Clip:
    id: str
    dir: str | None = None        # a clip directory...
    film: str = 'film.py'         # ...and its film file, relative to `dir`
    footage: str | None = None    # or a footage file, from `in` to `out`
    in_frame: int = 0
    out_frame: int = 0
    head: int = 0
    tail: int = 0
    cut: Cut = field(default_factory=Cut)
    sound: ClipSound = field(default_factory=ClipSound)

    @property
    def is_footage(self):
        return self.footage is not None

    @property
    def film_path(self):
        """The film file, relative to the video's root (code clips only)."""
        return f'{self.dir}/{self.film}' if self.dir else None


@dataclass(frozen=True)
class Act:
    title: str
    clips: tuple


@dataclass(frozen=True)
class LaneItem:
    sound: str | None             # a file; None for a sound effect...
    at: int
    frames: int
    offset: int = 0
    gain_db: float = 0.0
    fade_in: int = DEFAULT_FADE
    fade_out: int = DEFAULT_FADE
    cue: SfxCue | None = None     # ...from the pack, its align point on `at`


@dataclass(frozen=True)
class Lane:
    name: str                     # "Audio 1", "Audio 2"...: from its position
    items: tuple = ()
    duck: bool = False
    duck_db: float = DEFAULT_DUCK_DB
    mute: bool = False            # kept in the file, left out of the mix


@dataclass(frozen=True)
class Beats:
    """A reel's beat grid: the song on Audio `lane`, its item `item` (both
    counted from 1), at `bpm`, its first beat `first` frames into its file."""
    lane: int
    item: int
    bpm: float
    first: int = 0
    bar: int = 4


@dataclass(frozen=True)
class Timeline:
    fps: int
    formats: tuple
    clips: tuple
    acts: tuple = ()
    lanes: tuple = ()
    version: int = VERSION
    beats: Beats | None = None

    def clip(self, clip_id):
        for c in self.clips:
            if c.id == clip_id:
                return c
        raise KeyError(clip_id)


def lane_name(index):
    """The user-facing name of the lane at 0-based `index`."""
    return f'Audio {index + 1}'


# ---- validation ----

class _Checker:
    def __init__(self):
        self.problems = []

    def bad(self, where, msg):
        self.problems.append(f'{where}: {msg}' if where else msg)

    def keys(self, where, obj, allowed, required=()):
        if not isinstance(obj, dict):
            self.bad(where, f'must be an object, not {_kind(obj)}')
            return False
        for k in obj:
            if k not in allowed:
                near = difflib.get_close_matches(k, allowed, n=1)
                hint = (f' ({HINTS[k]})' if k in HINTS and HINTS[k] else
                        f' (did you mean "{near[0]}"?)' if near else f'; allowed: {", ".join(allowed)}')
                self.bad(where, f'unknown key "{k}"{hint}')
        for k in required:
            if k not in obj:
                self.bad(where, f'needs "{k}"')
        return True

    def int_(self, where, obj, key, default=0, minimum=0):
        v = obj.get(key, default)
        if isinstance(v, bool) or not isinstance(v, int):
            self.bad(where, f'{key} must be a whole number of frames, not {_kind(v)}')
            return default
        if v < minimum:
            self.bad(where, f'{key} must be at least {minimum}, not {v}')
            return default
        return v

    def num(self, where, obj, key, default=0.0, lo=-60.0, hi=24.0):
        v = obj.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            self.bad(where, f'{key} must be a number, not {_kind(v)}')
            return default
        if not lo <= v <= hi:
            self.bad(where, f'{key} must be between {lo:g} and {hi:g}, not {v:g}')
            return default
        return float(v)

    def bool_(self, where, obj, key, default=False):
        v = obj.get(key, default)
        if not isinstance(v, bool):
            self.bad(where, f'{key} must be true or false, not {_kind(v)}')
            return default
        return v

    def path(self, where, obj, key):
        v = obj.get(key)
        if not isinstance(v, str) or not v:
            self.bad(where, f'{key} must be a path relative to the video\'s root')
            return None
        p = PurePosixPath(v)
        if '\\' in v or p.is_absolute() or '..' in p.parts or v.startswith('~'):
            self.bad(where, f'{key} "{v}" must be a relative path inside the video (no "..", no leading "/")')
            return None
        return str(p)


def _kind(v):
    return {dict: 'an object', list: 'a list', str: 'a string', bool: 'true/false',
            type(None): 'null'}.get(type(v), type(v).__name__)


def _parse_cue(ck, where, raw, extra=()):
    """An `SfxCue` from a lane item or a cut's `sound` object; None when it doesn't validate."""
    if not ck.keys(where, raw, SFX_KEYS + tuple(extra), ('sfx',)):
        return None
    sfx = raw['sfx']
    if not isinstance(sfx, str) or not (_SFX_ID.match(sfx) or sfx == 'auto'):
        ck.bad(where, f'sfx must be a sound effect\'s id ("whoosh_fast/tight"; `python -m videobuilder sfx list`), '
                      f'not {json.dumps(sfx)}')
        return None
    if sfx == 'auto' and 'at' in extra:
        ck.bad(where, 'sfx "auto" is for a cut\'s sound; name the sound effect for a lane')
        return None
    variant, note = raw.get('variant'), raw.get('note')
    if variant is not None and note is not None:
        ck.bad(where, 'give a variant or a note, not both')
    if variant is not None and (not isinstance(variant, str) or not re.fullmatch(r'[A-Za-z0-9.]+', variant)):
        ck.bad(where, f'variant must be a take\'s name ("0.8s", "C5"), not {json.dumps(variant)}')
        variant = None
    if note is not None:
        from .sfx import note_name
        try:
            note = note_name(note)
        except ValueError as e:
            ck.bad(where, f'note: {e}')
            note = None
    align = raw.get('align', 'peak')
    if align not in ('peak', 'onset'):
        ck.bad(where, f'align must be "peak" or "onset", not {json.dumps(align)}')
        align = 'peak'
    return SfxCue(sfx, variant, note, ck.int_(where, raw, 'frames'), align, ck.num(where, raw, 'gain_db'),
                  ck.bool_(where, raw, 'through'))


def _parse_cut(ck, where, raw, first):
    if raw is None:
        return Cut()
    if not ck.keys(where + '.cut', raw, ('transition', 'frames', 'direction', 'sound'), ('transition',)):
        return Cut()
    w = where + '.cut'
    kind = raw.get('transition')
    if kind in LATER_TRANSITIONS:
        ck.bad(w, f'transition "{kind}" is not available yet; use one of {", ".join(TRANSITIONS)}')
        return Cut()
    if kind not in TRANSITIONS:
        ck.bad(w, f'transition must be one of {", ".join(TRANSITIONS)}, not {json.dumps(kind)}')
        return Cut()
    frames = ck.int_(w, raw, 'frames', 0)
    direction = raw.get('direction', 'left')
    if 'direction' in raw and kind not in DIRECTED:
        ck.bad(w, 'direction is for a wipe or a whip only')
    elif direction not in WIPE_DIRECTIONS:
        ck.bad(w, f'direction must be one of {", ".join(WIPE_DIRECTIONS)}, not {json.dumps(direction)}')
        direction = 'left'
    if kind == 'cut' and frames:
        ck.bad(w, f'a cut has no length; drop frames or use a dissolve ({frames} given)')
        frames = 0
    elif kind != 'cut' and not frames and 'frames' in raw:
        ck.bad(w, f'a {kind} needs frames of at least 1')
    elif kind != 'cut' and 'frames' not in raw:
        ck.bad(w, f'a {kind} needs "frames", its length')
    if first and kind != 'cut':
        ck.bad(w, 'the first clip has no clip before it to transition from')
        return Cut()
    sound = raw.get('sound')
    if sound is not None:
        if first:
            ck.bad(w, 'the first clip has no cut into it to put a sound on')
            sound = None
        elif isinstance(sound, str):
            sound = _parse_cue(ck, w + '.sound', {'sfx': sound})
        else:
            sound = _parse_cue(ck, w + '.sound', sound)
    if sound is not None and sound.sfx == 'auto' and kind not in AUTO_SOUNDS:
        ck.bad(w, f'sound "auto" knows a whip (a whoosh) and a flash (a hit); name the sound effect for a {kind}')
        sound = None
    return Cut(kind, frames, direction, sound)


def _parse_sound(ck, where, raw):
    if raw is None:
        return ClipSound()
    if not ck.keys(where + '.sound', raw, ('gain_db', 'early', 'late', 'dialogue')):
        return ClipSound()
    w = where + '.sound'
    return ClipSound(ck.num(w, raw, 'gain_db'), ck.int_(w, raw, 'early'), ck.int_(w, raw, 'late'),
                     ck.bool_(w, raw, 'dialogue'))


CLIP_KEYS = ('id', 'dir', 'film', 'footage', 'in', 'out', 'head', 'tail', 'cut', 'sound')


def _parse_clip(ck, i, raw, seen):
    where = f'clips[{i}]'
    cid = raw.get('id') if isinstance(raw, dict) else None
    named = isinstance(cid, str) and _ID_RE.fullmatch(cid)
    if named:
        where = f'{where} "{cid}"'
    if not ck.keys(where, raw, CLIP_KEYS, ('id',)):
        return None
    if not named:
        if 'id' in raw:
            ck.bad(where, f'id must be lowercase letters, digits and dashes, not {json.dumps(cid)}')
        cid = f'#{i}'
    else:
        if cid in seen:
            ck.bad(where, 'id is used by an earlier clip too; ids must be unique')
        seen.add(cid)
    kw = {}
    if ('dir' in raw) == ('footage' in raw):
        ck.bad(where, 'needs exactly one of "dir" (a clip directory with its own film) '
                      'or "footage" (a source file cut in/out)')
    elif 'dir' in raw:
        kw['dir'] = ck.path(where, raw, 'dir')
        if 'film' in raw:
            film = raw['film']
            if not isinstance(film, str) or '/' in film or not film.endswith('.py'):
                ck.bad(where, f'film must be a .py file name inside dir, not {json.dumps(film)}')
            else:
                kw['film'] = film
        for k in ('in', 'out'):
            if k in raw:
                ck.bad(where, f'"{k}" is for footage clips; trim a clip directory with head/tail')
    else:
        kw['footage'] = ck.path(where, raw, 'footage')
        if 'film' in raw:
            ck.bad(where, '"film" is for clip directories, not footage')
        if 'out' not in raw:
            ck.bad(where, 'a footage clip needs "out", the frame it ends before')
        kw['in_frame'] = ck.int_(where, raw, 'in')
        kw['out_frame'] = ck.int_(where, raw, 'out', minimum=1) if 'out' in raw else 1
        if kw['out_frame'] <= kw['in_frame']:
            ck.bad(where, f'out ({kw["out_frame"]}) must be after in ({kw["in_frame"]})')
    kw['head'] = ck.int_(where, raw, 'head')
    kw['tail'] = ck.int_(where, raw, 'tail')
    if kw.get('footage') and kw['head'] + kw['tail'] >= kw['out_frame'] - kw['in_frame'] > 0:
        ck.bad(where, f'head + tail ({kw["head"] + kw["tail"]}) trims away all '
                      f'{kw["out_frame"] - kw["in_frame"]} frames between in and out')
    kw['cut'] = _parse_cut(ck, where, raw.get('cut'), i == 0)
    kw['sound'] = _parse_sound(ck, where, raw.get('sound'))
    return Clip(cid, **kw)


def _parse_lane(ck, i, raw):
    name = lane_name(i)
    where = f'lanes[{i}] ({name})'
    if not ck.keys(where, raw, ('items', 'duck', 'duck_db', 'mute')):
        return Lane(name)
    duck = ck.bool_(where, raw, 'duck')
    mute = ck.bool_(where, raw, 'mute')
    duck_db = ck.num(where, raw, 'duck_db', DEFAULT_DUCK_DB, lo=-60.0, hi=0.0)
    if 'duck_db' in raw and not duck:
        ck.bad(where, 'duck_db is set but duck is not true')
    items = raw.get('items', [])
    if not isinstance(items, list):
        ck.bad(where, f'items must be a list, not {_kind(items)}')
        items = []
    out = []
    for j, item in enumerate(items):
        w = f'{name}, item {j + 1}'
        if isinstance(item, dict) and 'sfx' in item:
            if 'sound' in item:
                ck.bad(w, 'needs one of "sound" (a file) or "sfx" (a sound effect from the pack), not both')
                continue
            cue = _parse_cue(ck, w, item, ('at',))
            if 'at' not in item:
                ck.bad(w, 'needs "at", the frame its peak (or onset) lands on')
            if cue is not None:
                out.append(LaneItem(None, ck.int_(w, item, 'at'), cue.frames, gain_db=cue.gain_db, cue=cue))
            continue
        if not ck.keys(w, item, ('sound', 'at', 'offset', 'frames', 'gain_db', 'fade_in', 'fade_out'),
                       ('sound', 'at', 'frames')):
            continue
        out.append(LaneItem(ck.path(w, item, 'sound'), ck.int_(w, item, 'at'),
                            ck.int_(w, item, 'frames', 1, minimum=1), ck.int_(w, item, 'offset'),
                            ck.num(w, item, 'gain_db'), ck.int_(w, item, 'fade_in', DEFAULT_FADE),
                            ck.int_(w, item, 'fade_out', DEFAULT_FADE)))
    return Lane(name, tuple(out), duck, duck_db, mute)


def _parse_acts(ck, raw, order):
    if not isinstance(raw, list):
        ck.bad('acts', f'must be a list, not {_kind(raw)}')
        return ()
    acts, last = [], -1
    for i, act in enumerate(raw):
        where = f'acts[{i}]'
        if not ck.keys(where, act, ('title', 'clips'), ('title', 'clips')):
            continue
        title = act['title']
        if not isinstance(title, str) or not title.strip():
            ck.bad(where, 'title must be some text')
        clips = act['clips']
        if not isinstance(clips, list) or not clips or not all(isinstance(c, str) for c in clips):
            ck.bad(where, 'clips must be a non-empty list of clip ids')
            continue
        unknown = [c for c in clips if c not in order]
        if unknown:
            ck.bad(where, f'no clip with id {", ".join(json.dumps(c) for c in unknown)}')
            continue
        idx = [order[c] for c in clips]
        if idx != list(range(idx[0], idx[0] + len(idx))):
            ck.bad(where, 'clips must be consecutive clips, in timeline order')
            continue
        if idx[0] <= last:
            ck.bad(where, 'acts must not overlap and must be in timeline order')
            continue
        last = idx[-1]
        acts.append(Act(title, tuple(clips)))
    return tuple(acts)


BEATS_KEYS = ('lane', 'item', 'bpm', 'first', 'bar')


def _parse_beats(ck, raw, lanes):
    if not ck.keys('beats', raw, BEATS_KEYS, ('lane', 'item', 'bpm')):
        return None
    lane = ck.int_('beats', raw, 'lane', 1, minimum=1)
    item = ck.int_('beats', raw, 'item', 1, minimum=1)
    bpm = ck.num('beats', raw, 'bpm', 120.0, lo=30.0, hi=300.0)
    first = ck.int_('beats', raw, 'first')
    bar = ck.int_('beats', raw, 'bar', 4, minimum=1)
    if bar > 16:
        ck.bad('beats', f'bar must be at most 16 beats, not {bar}')
    if lane > len(lanes):
        ck.bad('beats', f'lane {lane}: there is no Audio {lane} (the timeline has {len(lanes)} '
                        f'lane{"" if len(lanes) == 1 else "s"})')
    elif item > len(lanes[lane - 1].items):
        ck.bad('beats', f'item {item}: Audio {lane} has {len(lanes[lane - 1].items)} item'
                        f'{"" if len(lanes[lane - 1].items) == 1 else "s"}')
    elif lanes[lane - 1].items[item - 1].cue is not None:
        ck.bad('beats', f'item {item} of Audio {lane} is a sound effect; the beats are a song\'s')
    return Beats(lane, item, bpm, first, bar)


def parse(data, source=NAME):
    """The `Timeline` of an already-decoded timeline file; raises
    `TimelineError` naming every problem found."""
    from .film import FORMATS
    ck = _Checker()
    if not ck.keys('', data, ('version', 'fps', 'formats', 'clips', 'acts', 'lanes', 'beats'), ('version', 'clips')):
        raise TimelineError(source, ck.problems)
    if data.get('version') != VERSION:
        ck.bad('version', f'must be {VERSION}, not {json.dumps(data.get("version"))}')
    fps = ck.int_('', data, 'fps', 30, minimum=1)
    if fps > 120:
        ck.bad('', f'fps must be at most 120, not {fps}')
    formats = data.get('formats', ['16x9'])
    if not isinstance(formats, list) or not formats or not all(isinstance(f, str) for f in formats):
        ck.bad('formats', 'must be a non-empty list of format names')
        formats = ['16x9']
    for f in formats:
        if f not in FORMATS:
            ck.bad('formats', f'unknown format {json.dumps(f)}; known: {", ".join(FORMATS)}')
    raw_clips = data.get('clips')
    clips, seen = [], set()
    if not isinstance(raw_clips, list) or not raw_clips:
        ck.bad('clips', 'must be a non-empty list')
        raw_clips = []
    for i, raw in enumerate(raw_clips):
        c = _parse_clip(ck, i, raw, seen)
        if c is not None:
            clips.append(c)
    _check_overlaps(ck, clips)
    order = {c.id: i for i, c in enumerate(clips)}
    acts = _parse_acts(ck, data['acts'], order) if 'acts' in data else ()
    raw_lanes = data.get('lanes', [])
    if not isinstance(raw_lanes, list):
        ck.bad('lanes', f'must be a list, not {_kind(raw_lanes)}')
        raw_lanes = []
    lanes = tuple(_parse_lane(ck, i, raw) for i, raw in enumerate(raw_lanes))
    beats = _parse_beats(ck, data['beats'], lanes) if 'beats' in data else None
    if ck.problems:
        raise TimelineError(source, ck.problems)
    return Timeline(fps, tuple(formats), tuple(clips), acts, lanes, beats=beats)


def _check_overlaps(ck, clips):
    """What can be checked without a clip's length: footage clips know theirs."""
    for i, c in enumerate(clips):
        if not c.is_footage:
            continue
        n = c.out_frame - c.in_frame - c.head - c.tail
        d_in = c.cut.frames
        d_out = clips[i + 1].cut.frames if i + 1 < len(clips) else 0
        if n > 0 and d_in + d_out > n:
            ck.bad(f'clips[{i}] "{c.id}"', f'its transitions ({d_in} in, {d_out} out) are longer '
                                            f'than the {n} frames it shows')


def loads(text, source=NAME):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise TimelineError(source, [f'not valid JSON: {e.msg} at line {e.lineno} column {e.colno}']) from None
    return parse(data, source)


def load(path):
    """The `Timeline` in the file at `path`."""
    with open(path, encoding='utf-8') as fh:
        return loads(fh.read(), os.fspath(path))


def find(root):
    """`<root>/timeline.json` if the video at `root` is a film made of clips, else None."""
    path = os.path.join(root, NAME)
    return path if os.path.isfile(path) else None


# ---- placement ----

@dataclass(frozen=True)
class Placement:
    """Where a clip lands in the assembly. `start`: its first visible frame on
    the timeline; `frames`: how many it shows; `source`: the frame of its media
    (the clip's render, or the footage file) shown first; `media_frames`: the
    media's whole length, so J/L cuts know how much sound lies past the trims."""
    clip: Clip
    start: int
    frames: int
    source: int
    media_frames: int

    @property
    def end(self):
        return self.start + self.frames


def place(timeline, lengths, known=False):
    """([Placement] for every clip, the film's total frames), given `lengths`
    {clip id: frames} of each clip directory's render and, optionally, of each
    footage file (else taken to end at `out`). A transition of d frames overlaps the clip with the
    one before it by d. Raises ValueError for trims or transitions a clip is
    too short for. With `known`, stops at the first clip directory whose
    length isn't in `lengths` (its placements are the clips before it; the
    total, where they end)."""
    out, at = [], 0
    for i, c in enumerate(timeline.clips):
        if known and not c.is_footage and c.id not in lengths:
            break
        if c.is_footage:
            media, source = lengths.get(c.id, c.out_frame), c.in_frame + c.head
            frames = c.out_frame - c.in_frame - c.head - c.tail
            if media < c.out_frame:
                raise ValueError(f'clip "{c.id}": out is frame {c.out_frame}, but {c.footage} '
                                 f'is only {media} frames long at {timeline.fps} fps')
        else:
            media = lengths[c.id]
            source, frames = c.head, media - c.head - c.tail
        if frames < 1:
            raise ValueError(f'clip "{c.id}": head {c.head} + tail {c.tail} trims away all {media} of its frames')
        d_in = c.cut.frames if i else 0
        d_out = timeline.clips[i + 1].cut.frames if i + 1 < len(timeline.clips) else 0
        if d_in + d_out > frames:
            raise ValueError(f'clip "{c.id}": its transitions ({d_in} in, {d_out} out) are longer '
                             f'than the {frames} frames it shows')
        start = at - d_in
        out.append(Placement(c, start, frames, source, media))
        at = start + frames
    return out, at


# ---- beats ----

def beat_grid(timeline):
    """The `beats.BeatGrid` of a reel's song on the timeline, or None for a
    timeline with no beat grid: its beats from where the song's item starts
    playing to where it stops."""
    from .beats import BeatGrid
    b = timeline.beats
    if b is None:
        return None
    item = timeline.lanes[b.lane - 1].items[b.item - 1]
    return BeatGrid(timeline.fps, b.bpm, zero=item.at - item.offset + b.first, lo=item.at,
                    hi=item.at + item.frames, bar=b.bar)


def cut_frame(placement):
    """Where the cut into a placed clip is on the timeline: a hard cut's first
    frame of the clip; a transition's middle (rounded down)."""
    return placement.start + placement.clip.cut.frames // 2


def offbeat(timeline, placements):
    """Warnings, one per cut in `placements` that a reel's beat grid has off
    its beats (none without a grid, and none for a cut outside the song)."""
    grid = beat_grid(timeline)
    if grid is None:
        return []
    out = []
    for i, p in enumerate(placements[1:], start=1):
        f = cut_frame(p)
        if not grid.lo <= f <= grid.hi:
            continue
        off = grid.off(f)
        if off:
            near = grid.snap(f)
            other = grid.step(f, 1 if off > 0 else -1)
            what = 'cut' if p.clip.cut.transition == 'cut' else f'{p.clip.cut.transition}\'s middle'
            out.append(f'clips[{i}] "{p.clip.id}": the {what} into it is at frame {f}, {abs(off)} '
                       f'frame{"" if abs(off) == 1 else "s"} {"after" if off > 0 else "before"} '
                       f'{grid.describe(near)} (frame {near}); put it on {near} or {other}')
    return out


def snap_cuts(data, lengths=None):
    """(a copy of the timeline file `data` with every cut that its beat grid
    has off a beat moved onto one, [what moved]). A cut moves by changing how
    long the clip before it shows: a footage clip's `out` (or its `tail`,
    while it has one to give back), a clip directory's `tail`. It goes to the
    nearest beat, or the beat on its other side when the clip can't reach
    that one (too short, or its file ends). `lengths` is as for `place`: a
    clip directory with no length stops the snapping there, as do cuts
    after it. Raises ValueError for a timeline with no beat grid."""
    import copy
    data = copy.deepcopy(data)
    lengths = dict(lengths or {})
    timeline = parse(data)
    grid = beat_grid(timeline)
    if grid is None:
        raise ValueError('the timeline has no beat grid ("beats"): there are no beats to snap to')
    moves = []
    for i in range(1, len(timeline.clips)):
        placements, _ = place(parse(data), lengths, known=True)
        if len(placements) <= i:
            moves.append(f'stopped at clips[{len(placements)}]: its length is known once it renders')
            break
        f = cut_frame(placements[i])
        if not grid.lo <= f <= grid.hi or grid.on_beat(f):
            continue
        near = grid.snap(f)
        for target in (near, grid.step(f, -1 if near > f else 1)):
            trial = _moved(data, i - 1, target - f)
            if trial is None:
                continue
            try:
                place(parse(trial), lengths, known=True)
            except (ValueError, TimelineError):
                continue
            data = trial
            moves.append(f'clips[{i}] "{placements[i].clip.id}": cut moved from frame {f} to {target} '
                         f'({grid.describe(target)})')
            break
        else:
            moves.append(f'clips[{i}] "{placements[i].clip.id}": the cut at frame {f} cannot reach a beat; '
                         'change the clips either side of it')
    return data, moves


def _moved(data, i, delta):
    """A copy of `data` with clip `i` showing `delta` frames more (fewer, if
    negative), or None when it can't."""
    import copy
    data = copy.deepcopy(data)
    c = data['clips'][i]
    tail = c.get('tail', 0)
    if 'footage' in c:
        give = min(tail, delta) if delta > 0 else 0
        tail -= give
        c['out'] = c['out'] + delta - give
        if c['out'] <= c.get('in', 0):
            return None
    else:
        tail -= delta
        if tail < 0:
            return None
    if tail:
        c['tail'] = tail
    else:
        c.pop('tail', None)
    return data

"""Pre-production: a video's bible before production starts (see
docs/preproduction.md for the full picture of what each file means to a
user). Everything pre-production holds lives under `bible/`, beside Film
details' `bible.md` and `bible/characters/` (film_setup.py):

    bible/phase.json          {"phase": "pre-production"|"production"}
    bible/script.fountain     the screenplay, in Fountain (fountain.py)
    bible/scenes.json         scene cards (songs + scenes)
    bible/options/<id>.json   one option set; its images beside it in
                               bible/options/<id>/

Most of this module is pure data: parsing, validating and building the
bytes of those files from a directory on disk (the working tree at some
commit), the same shape as film_setup.py; it raises no HTTPError and never
touches git. preprod_api.py is the editor-facing layer that commits these
files and exposes them over the API. The one exception is `PreprodBrief`,
`NoteStore.preproduction` (see film_brief.FilmBrief for the same pattern):
it reads the phase at main's tip, so it does reach into git and the
editor.
"""
import json
import re

from . import film_setup
from .notes import CHOICE_IMAGE_KINDS, valid_choice_image

PHASES = ('pre-production', 'production')
PHASE_FILE = 'bible/phase.json'
SCRIPT_FILE = 'bible/script.fountain'
SCENES_FILE = 'bible/scenes.json'
OPTIONS_DIR = 'bible/options'

SET_TOPICS = ('look', 'character', 'scene', 'other')
OPTIONS_MIN, OPTIONS_MAX = 2, 4
OPTION_KEYS = ('A', 'B', 'C', 'D')
LABEL_MAX, TEXT_MAX, QUESTION_MAX = 80, 400, 200
SWATCHES_MAX = 5
_OTHER_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,59}$')
_SWATCH_RE = re.compile(r'^#[0-9a-fA-F]{6}$')
# The same id shape as a timeline clip id (timeline_file._ID_RE): a scene's id
# becomes the planned clip id production makes from it (see docs/preproduction.md).
_SIMPLE_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')


# ---- phase ----

def _phase_from_bytes(data):
    if data is None:
        return 'production'
    try:
        parsed = json.loads(data)
    except ValueError:
        return 'production'
    phase = parsed.get('phase') if isinstance(parsed, dict) else None
    return phase if phase in PHASES else 'production'


def read_phase(directory):
    """The video's phase, read from its working tree. Missing, unreadable or
    unknown counts as 'production': an existing video with no phase file is
    in production, with no migration needed."""
    try:
        data = (directory / PHASE_FILE).read_bytes()
    except OSError:
        data = None
    return _phase_from_bytes(data)


def phase_bytes(phase):
    if phase not in PHASES:
        raise ValueError(f'unknown phase {phase!r}')
    return (json.dumps({'phase': phase}) + '\n').encode()


class PreprodBrief:
    """NoteStore.preproduction: (video, note, state) -> {} once the video
    is in pre-production on main, else None, so a video in
    production renders byte-identical to before pre-production existed.

    Main, not the builder's draft: the phase is the director's switch
    (POST /api/phase commits it on main), and an unlanded draft carries
    whatever phase it branched from -- reading it there would brief Start
    production's own note as pre-production, and disagree with the render
    gate (Editor.phase), which reads main."""

    def __init__(self, editor):
        self.editor = editor

    def __call__(self, video, note, state):
        from .clip_cache import GitTree
        from .drafts import git
        e = self.editor
        try:
            sha = git(e.root, 'rev-parse', '--verify', 'main^{commit}')
        except ValueError:
            return None
        directory = e.drafts.context(video)['directory']
        if _phase_from_bytes(GitTree(e.root, sha, directory).read(PHASE_FILE)) != 'pre-production':
            return None
        return {}


# ---- raw bible.md sections the builder writes freely (Film details doesn't own them) ----

def read_bible_section(directory, name):
    """The raw text of bible.md's `## <name>` section, '' without one -- for
    sections no sheet writes (Logline, and Look's free-text summary in
    pre-production)."""
    try:
        md = (directory / film_setup.BIBLE).read_text(errors='replace')
    except OSError:
        return ''
    body, found = [], False
    for line in md.splitlines():
        if line.startswith('## '):
            found = line[3:].strip() == name
        elif found:
            body.append(line)
    return '\n'.join(body).strip()


def read_logline(directory):
    return read_bible_section(directory, 'Logline')


# ---- option sets ----

def set_path(set_id):
    return f'{OPTIONS_DIR}/{set_id}.json'


def set_image_dir(set_id):
    return f'{OPTIONS_DIR}/{set_id}'


def set_id_for_character(slug):
    return f'character-{slug}'


def set_id_for_scene(scene_id):
    return f'scene-{scene_id}'


def _text(value, what, limit, required=True):
    if not isinstance(value, str):
        raise ValueError(f'{what} must be text')
    value = value.strip()
    if required and not value:
        raise ValueError(f'{what} is required')
    if len(value) > limit:
        raise ValueError(f'{what} must be at most {limit} characters')
    return value


def _parse_option(raw, index):
    if not isinstance(raw, dict):
        raise ValueError(f'options[{index}] must be an object')
    key = raw.get('key')
    if key not in OPTION_KEYS:
        raise ValueError(f'options[{index}].key must be one of {", ".join(OPTION_KEYS)}')
    label = _text(raw.get('label'), f'options[{index}].label', LABEL_MAX)
    text = _text(raw.get('text'), f'options[{index}].text', TEXT_MAX)
    image, kind = raw.get('image'), raw.get('kind')
    if image is not None:
        if not valid_choice_image(image):
            raise ValueError(f'options[{index}].image must be a picture under bible/')
        if kind not in CHOICE_IMAGE_KINDS:
            raise ValueError(f'options[{index}].kind must be one of {", ".join(CHOICE_IMAGE_KINDS)}')
    elif kind is not None:
        raise ValueError(f'options[{index}].kind requires an image')
    out = {'key': key, 'label': label, 'text': text, 'image': image, 'kind': kind}
    swatches = raw.get('swatches')
    if swatches is not None:
        if not isinstance(swatches, list) or len(swatches) > SWATCHES_MAX \
                or not all(isinstance(s, str) and _SWATCH_RE.match(s) for s in swatches):
            raise ValueError(f'options[{index}].swatches must be up to {SWATCHES_MAX} "#rrggbb" colours')
        out['swatches'] = swatches
    return out


def parse_option_set(body):
    """A validated option-set dict from a POST body, or raises ValueError.
    Does not check the pick against a scene/character that actually exists
    -- the caller (preprod_api) knows the video's own scenes and characters,
    this module only knows the shape."""
    topic = body.get('topic')
    if topic not in SET_TOPICS:
        raise ValueError(f'topic must be one of {", ".join(SET_TOPICS)}')
    set_id = body.get('id')
    if not isinstance(set_id, str):
        raise ValueError('id must be a string')
    out = {'id': set_id, 'topic': topic}
    if topic == 'character':
        character = body.get('character')
        if not isinstance(character, str) or not _OTHER_ID_RE.match(character):
            raise ValueError('character must be a slug')
        if set_id != set_id_for_character(character):
            raise ValueError(f'id must be {set_id_for_character(character)!r} for a character set')
        out['character'] = character
    elif topic == 'scene':
        scene = body.get('scene')
        if not isinstance(scene, str) or not _SIMPLE_ID_RE.match(scene):
            raise ValueError('scene must be a scene id')
        if set_id != set_id_for_scene(scene):
            raise ValueError(f'id must be {set_id_for_scene(scene)!r} for a scene set')
        out['scene'] = scene
    elif topic == 'look':
        if set_id != 'look':
            raise ValueError('id must be "look" for the look set')
    else:
        if not _OTHER_ID_RE.match(set_id):
            raise ValueError('id must match [a-z0-9][a-z0-9-]{0,59}')
    out['question'] = _text(body.get('question') or '', 'question', QUESTION_MAX, required=False)
    options = body.get('options')
    if not isinstance(options, list) or not OPTIONS_MIN <= len(options) <= OPTIONS_MAX:
        raise ValueError(f'options must be a list of {OPTIONS_MIN}-{OPTIONS_MAX}')
    out['options'] = [_parse_option(o, i) for i, o in enumerate(options)]
    keys = [o['key'] for o in out['options']]
    if len(keys) != len(set(keys)):
        raise ValueError('option keys must be unique')
    pick = body.get('pick')
    if pick is not None and pick not in keys:
        raise ValueError('pick must be one of the options\' keys, or null')
    out['pick'] = pick
    return out


def set_bytes(data):
    ordered = {'id': data['id'], 'topic': data['topic']}
    if 'character' in data:
        ordered['character'] = data['character']
    if 'scene' in data:
        ordered['scene'] = data['scene']
    ordered['question'] = data['question']
    ordered['pick'] = data['pick']
    ordered['options'] = data['options']
    return (json.dumps(ordered, indent=2) + '\n').encode()


def read_set(directory, set_id):
    """The option set `set_id`, or None if there is no such file. Raises
    ValueError for a file that exists but doesn't parse -- the caller
    (preprod_api.read_board) is expected to catch that and report it in
    `problems` rather than fail the whole page."""
    path = directory / set_path(set_id)
    try:
        text = path.read_text()
    except OSError:
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f'{set_path(set_id)}: {exc}') from None
    if not isinstance(data, dict) or data.get('id') != set_id:
        raise ValueError(f'{set_path(set_id)}: not a valid option set')
    # The builder writes these files by hand, so a parseable file can still be the wrong shape;
    # everything downstream (the board, the checklist, picks) indexes fields directly.
    try:
        return parse_option_set(data)
    except ValueError as exc:
        raise ValueError(f'{set_path(set_id)}: {exc}') from None


def list_set_ids(directory):
    folder = directory / OPTIONS_DIR
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob('*.json'))


def delete_set_files(directory, set_id):
    """{path: None, ...} removing the set file and every image beside it,
    for commit_files."""
    out = {set_path(set_id): None}
    folder = directory / set_image_dir(set_id)
    if folder.is_dir():
        for p in folder.iterdir():
            if p.is_file():
                out[f'{set_image_dir(set_id)}/{p.name}'] = None
    return out


# ---- scenes ----

def _song_ids(raws):
    ids = []
    for i, raw in enumerate(raws):
        if not isinstance(raw, dict):
            raise ValueError(f'songs[{i}] must be an object')
        sid = raw.get('id')
        if not isinstance(sid, str) or not _SIMPLE_ID_RE.match(sid):
            raise ValueError(f'songs[{i}].id must match [a-z0-9][a-z0-9-]*')
        ids.append(sid)
    if len(ids) != len(set(ids)):
        raise ValueError('song ids must be unique')
    return ids


def _parse_section(raw, i, j):
    if not isinstance(raw, dict):
        raise ValueError(f'songs[{i}].sections[{j}] must be an object')
    name = _text(raw.get('name'), f'songs[{i}].sections[{j}].name', 80)
    start, end = raw.get('start'), raw.get('end')
    if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0:
        raise ValueError(f'songs[{i}].sections[{j}].start must be a nonnegative number')
    if not isinstance(end, (int, float)) or isinstance(end, bool) or end <= start:
        raise ValueError(f'songs[{i}].sections[{j}].end must be greater than start')
    text = _text(raw.get('text') or '', f'songs[{i}].sections[{j}].text', TEXT_MAX, required=False)
    return {'name': name, 'start': start, 'end': end, 'text': text}


def _parse_song(raw, i):
    name = _text(raw.get('name'), f'songs[{i}].name', 120)
    file = _text(raw.get('file'), f'songs[{i}].file', 200)
    duration = raw.get('duration')
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0:
        raise ValueError(f'songs[{i}].duration must be a nonnegative number')
    bpm = raw.get('bpm')
    if bpm is not None and (not isinstance(bpm, (int, float)) or isinstance(bpm, bool) or bpm <= 0):
        raise ValueError(f'songs[{i}].bpm must be a positive number or null')
    mood = raw.get('mood')
    if mood is not None:
        mood = _text(mood, f'songs[{i}].mood', 80, required=False) or None
    sections = raw.get('sections') or []
    if not isinstance(sections, list):
        raise ValueError(f'songs[{i}].sections must be a list')
    return {'id': raw['id'], 'name': name, 'file': file, 'duration': duration, 'bpm': bpm, 'mood': mood,
            'sections': [_parse_section(s, i, j) for j, s in enumerate(sections)]}


def _parse_scene_look(raw, i):
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f'scenes[{i}].look must be an object or null')
    return {'name': _text(raw.get('name'), f'scenes[{i}].look.name', 80),
            'reason': _text(raw.get('reason') or '', f'scenes[{i}].look.reason', TEXT_MAX, required=False)}


def _parse_scene(raw, i, song_ids):
    if not isinstance(raw, dict):
        raise ValueError(f'scenes[{i}] must be an object')
    sid = raw.get('id')
    if not isinstance(sid, str) or not _SIMPLE_ID_RE.match(sid):
        raise ValueError(f'scenes[{i}].id must match [a-z0-9][a-z0-9-]*')
    slugline = _text(raw.get('slugline'), f'scenes[{i}].slugline', 200)
    summary = _text(raw.get('summary') or '', f'scenes[{i}].summary', TEXT_MAX, required=False)
    seconds = raw.get('seconds')
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
        raise ValueError(f'scenes[{i}].seconds must be a nonnegative number')
    song = raw.get('song')
    if song is not None and song not in song_ids:
        raise ValueError(f'scenes[{i}].song: no such song {song!r}')
    section, from_, to = raw.get('section'), raw.get('from'), raw.get('to')
    if section is not None:
        if song is None:
            raise ValueError(f'scenes[{i}].section needs a song')
        section = _text(section, f'scenes[{i}].section', 80)
    for name, value in (('from', from_), ('to', to)):
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0):
            raise ValueError(f'scenes[{i}].{name} must be a nonnegative number or null')
    if to is not None:
        if from_ is None:
            raise ValueError(f'scenes[{i}].to needs a from')
        if to <= from_:
            raise ValueError(f'scenes[{i}].to must be greater than from')
    return {'id': sid, 'slugline': slugline, 'summary': summary, 'seconds': seconds, 'song': song,
            'section': section, 'from': from_, 'to': to, 'look': _parse_scene_look(raw.get('look'), i)}


def parse_scenes(body):
    """A validated {'songs', 'scenes'} dict from a POST body, or raises
    ValueError."""
    raw_songs = body.get('songs') or []
    if not isinstance(raw_songs, list):
        raise ValueError('songs must be a list')
    song_ids = _song_ids(raw_songs)
    songs = [_parse_song(s, i) for i, s in enumerate(raw_songs)]
    raw_scenes = body.get('scenes') or []
    if not isinstance(raw_scenes, list):
        raise ValueError('scenes must be a list')
    scenes = [_parse_scene(s, i, song_ids) for i, s in enumerate(raw_scenes)]
    ids = [s['id'] for s in scenes]
    if len(ids) != len(set(ids)):
        raise ValueError('scene ids must be unique')
    return {'songs': songs, 'scenes': scenes}


def scenes_bytes(data):
    return (json.dumps(data, indent=2) + '\n').encode()


def read_scenes(directory):
    """The video's scene plan, or None without one. Raises ValueError for a
    file that doesn't parse (see read_set)."""
    try:
        text = (directory / SCENES_FILE).read_text()
    except OSError:
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f'{SCENES_FILE}: {exc}') from None
    if not isinstance(data, dict) or 'scenes' not in data:
        raise ValueError(f'{SCENES_FILE}: not a valid scene plan')
    try:
        return parse_scenes(data)
    except ValueError as exc:
        raise ValueError(f'{SCENES_FILE}: {exc}') from None


def clock(seconds):
    """`seconds` as m:ss, rounded down to the second."""
    seconds = int(seconds or 0)
    return f'{seconds // 60}:{seconds % 60:02d}'


# ---- checklist ----

def checklist(directory):
    """The pre-production checklist: 5 items, each {id, label, settled,
    detail}, derived from the bible -- never stored on its own. `problems`
    (malformed files) is collected by the caller (preprod_api.read_board)
    and doesn't affect settledness here: a set this can't read counts as
    not picked, same as a set that doesn't exist."""
    details = film_setup.read_details(directory)
    logline = read_logline(directory)

    def _set(set_id):
        try:
            return read_set(directory, set_id)
        except ValueError:
            return None

    try:
        script_text = (directory / SCRIPT_FILE).read_text()
    except OSError:
        script_text = None
    script_scenes = 0
    draft = None
    if script_text is not None:
        from . import fountain
        parsed = fountain.parse(script_text)
        script_scenes = len(parsed['scenes'])
        draft = parsed['draft']

    look_set = _set('look')
    look_settled = bool(look_set.get('pick')) if look_set is not None else bool(details.look)

    character_sets = [(c, _set(set_id_for_character(c['slug']))) for c in details.characters]
    cast_settled = bool(details.characters) and all(s is None or s.get('pick') for _, s in character_sets)

    try:
        scene_plan = read_scenes(directory)
    except ValueError:
        scene_plan = None
    scenes = scene_plan['scenes'] if scene_plan else []
    scene_sets = [(s, _set(set_id_for_scene(s['id']))) for s in scenes]
    scenes_settled = bool(scenes) and all(ss is None or ss.get('pick') for s, ss in scene_sets)

    return [
        {'id': 'logline', 'label': 'Logline', 'settled': bool(logline), 'detail': {'text': logline}},
        {'id': 'script', 'label': 'Script draft', 'settled': script_scenes > 0,
         'detail': {'draft': draft, 'scenes': script_scenes}},
        {'id': 'look', 'label': 'Look', 'settled': look_settled,
         'detail': {'label': _option_label(look_set) if look_set else (details.look or None)}},
        {'id': 'cast', 'label': 'Cast', 'settled': cast_settled,
         'detail': {'picked': [c['name'] for c, s in character_sets if s and s.get('pick')],
                    'open': [c['name'] for c, s in character_sets if s and not s.get('pick')]}},
        {'id': 'scenes', 'label': 'Scene plan', 'settled': scenes_settled,
         'detail': {'count': len(scenes), 'seconds': sum(s['seconds'] for s in scenes),
                    'open': [s['id'] for s, ss in scene_sets if ss and not ss.get('pick')]}},
    ]


def production_note_text(directory):
    """Start production's note text: what to build from, and -- since
    production can start with items still open -- which checklist items
    are, so the builder decides them itself and says what it decided."""
    items = checklist(directory)
    open_labels = [c['label'] for c in items if not c['settled']]
    lines = ['Start production: build the film from the bible, the script (bible/script.fountain) '
             'and the scene plan (bible/scenes.json).']
    if open_labels:
        lines.append('Still open: ' + ', '.join(open_labels) + '. Decide these yourself and say in your reply '
                     'what you decided.')
    return '\n\n'.join(lines)


def _option_label(option_set):
    pick = option_set.get('pick')
    if not pick:
        return None
    return next((o['label'] for o in option_set['options'] if o['key'] == pick), None)


"""Capability suggestions while a director types a note: the model reads the
catalog, the film's bible and timeline, the selected clip and the typed
text, and answers which looks, type styles, fonts, sound effects, capabilities
and (where configured) music fit it -- see suggest_client.py for the model
call itself, and suggest-notes.md (the design round that specified this) for
the full picture.

One `Suggest` exists wherever a model is configured (None otherwise, see
Editor.__init__/Library.__init__): it builds the two system blocks (a
static, cached catalog, and a per-video one), asks the client, validates
every id it gets back against the real catalog/fonts/sfx pack/music list
(an id or a span that doesn't check out is dropped silently, never shown),
caps the answer, caches it briefly so retyping or undoing is instant, and
records token usage per account. Nothing here ever raises past a bad
request shape; a model failure just answers no items, because a note box
must never show the director an error for this.

Unlike Pictures (one per project, sharing only its Artbox client), nothing
in `Suggest` is project-specific: the catalog, the answer cache and the
usage log all make sense shared across a whole library. So one `Suggest`
is built once -- at the Library in library mode, at the Editor in
single-project mode -- and `ask()` takes whichever project's Editor the
request is for (None for New video's "In a few words", asked before any
video exists)."""
import json
import re
import sys
import threading
import time
from pathlib import Path

from . import fonts as fonts_module
from . import sfx as sfx_module
from .editor import HTTPError, _account_key
from .suggest_client import SuggestCancelled, SuggestError

NEW_VIDEO_BLOCK = '(There is no video yet: the director is describing a brand new one before it exists.)'

STRONG_CAP = 5
RELATED_CAP = 8
MIN_WORDS = 3
CATALOG_TTL = 600  # seconds: the static block (catalog + fonts + sfx + music) is rebuilt this often
ANSWER_TTL = 300  # 5 minutes, per the design notes
ANSWER_CACHE_MAX = 500
MAX_WHY = 200
MAX_BIBLE_CHARS = 4000
_PUNCT_WS = re.compile(r'[\s,.;:!?]+')


def _normalize(text):
    """Collapses whitespace/punctuation differences, so retyping or a pick's
    own rewrite doesn't look like a new question to the answer cache."""
    return _PUNCT_WS.sub(' ', text.strip().lower()).strip()


def _capability_ids():
    """(looks ids, type ids, plain-capability ids), from the real catalog --
    never the family wrapper entries themselves ('looks', 'type'), which
    aren't things a note can ask for."""
    from . import capabilities
    looks, type_, caps = set(), set(), set()
    for e in capabilities.entries():
        family = e.get('family')
        if family == 'looks':
            looks.add(e['id'])
        elif family == 'type':
            type_.add(e['id'])
        elif e.get('children') is None:
            caps.add(e['id'])
    return looks, type_, caps


def _catalog_entry_line(e):
    family = e.get('family') or 'capabilities'
    prompts = ' / '.join(e.get('prompts', ())[:2])
    return f"{e['id']} | {family} | {e['title']} | {e['card']} | {prompts}"


def _build_static_block(music):
    """The static, cacheable system block: the catalog, fonts and sfx pack
    (always present), then music (only where configured, best-effort -- a
    source that can't be fetched right now is skipped rather than failing
    the whole block). Returns (text, known_music_ids)."""
    from . import capabilities
    lines = ['You are the suggestion engine behind a video builder\'s note box. Given a short note from a '
             'director, answer only with capabilities, looks, type styles, fonts, sound effects or music that '
             'what they wrote actually asks for. Say nothing rather than pad: an empty list is a fine answer. '
             'Never suggest something the bible or the note already names. Use "strong" only for a direct '
             'match; everything else related is "related". `span` must be the director\'s exact words (a '
             'substring of the note); `text` keeps their words and adds the unique name in plain words, e.g. '
             '"a friendlier font (Cantarell)" or "a whoosh (whoosh_fast/tight)". Answer JSON only: '
             '{"items": [{"id", "family" (one of looks/type/fonts/sfx/music/capabilities), "strength" '
             '("strong"|"related"), "why", "replace": {"span", "text"} or null}]}.',
             '', 'Catalog (id | family | title | card | example phrasings):']
    for e in capabilities.entries():
        if e.get('family') not in ('looks', 'type') and e.get('children') is not None:
            continue  # the family wrapper itself, not a pick
        lines.append(_catalog_entry_line(e))
    lines.append('')
    lines.append('Fonts (id | family | about):')
    for f in fonts_module.public():
        lines.append(f"{f['id']} | {f['family']} | {f['about']}")
    lines.append('')
    lines.append('Sound effects (id | role | family | about):')
    try:
        for effect in sfx_module.bank().find():
            lines.append(f'{effect.id} | {effect.role} | {effect.family} | {effect.about}')
    except sfx_module.SfxUnavailable:
        pass
    music_ids = set()
    if music:
        music_lines = []
        for source in music.list_sources():
            try:
                _, tracks = music.list_tracks(source['id'])
            except Exception:
                continue
            for t in tracks:
                music_ids.add(t['id'])
                music_lines.append(f"{t['id']} | {t['title']} | {', '.join(t.get('tags', ()))}")
        if music_lines:
            lines += ['', 'Music (id | title | tags):', *music_lines]
    return '\n'.join(lines), music_ids


def _video_block(editor, video):
    """The per-video system block: formats in use, a one-line-per-clip
    timeline summary, and the bible, when this video has one."""
    info = editor.info(video)
    lines = []
    formats = ', '.join(f['name'] for f in info.get('formats', ()))
    if formats:
        lines.append(f'Formats in use: {formats}')
    timeline = info.get('timeline')
    if timeline:
        lines.append('Timeline:')
        for seg in timeline.get('segments', [])[:80]:
            copy = ' '.join(str(v) for v in seg.get('copy', {}).values() if v)[:160]
            lines.append(f"- {seg['name']} (beat {seg['start']}-{seg['end']})" + (f': {copy}' if copy else ''))
    bible = _bible_text(editor, video)
    if bible:
        lines.append('Bible:')
        lines.append(bible)
    return '\n'.join(lines) if lines else '(no bible or timeline yet)'


def _bible_text(editor, video):
    try:
        path = Path(editor.project.video(video).path).parent / 'bible' / 'bible.md'
        return path.read_text(encoding='utf-8', errors='replace')[:MAX_BIBLE_CHARS] if path.is_file() else ''
    except (KeyError, OSError):
        return ''


def _user_text(surface, clip, at, text):
    lines = [f'Surface: {surface}']
    if clip:
        lines.append(f'Selected clip: {clip}')
    if isinstance(at, (int, float)) and not isinstance(at, bool):
        lines.append(f'Playhead: {at:.2f}s')
    lines.append(f'Note: {text}')
    return '\n'.join(lines)


class Suggest:
    """Built once (Editor.__init__ in single-project mode, Library.__init__
    in library mode, where every project's Editor shares this one instance
    via Editor(suggest=...)): validates and caches the model's answers, and
    keeps the per-account usage log. `music` is the shared MusicLibrary, or
    None; `has_accounts` is fixed for this process (library mode with
    --admin configured, else never), for the usage log's account grouping."""

    def __init__(self, state_dir, client, music=None, has_accounts=False):
        self.client = client
        self.music = music
        self.has_accounts = has_accounts
        self._looks_ids, self._type_ids, self._cap_ids = _capability_ids()
        self._catalog_lock = threading.Lock()
        self._catalog = None  # (text, music_ids, built_at)
        self._answer_lock = threading.Lock()
        self._answers = {}  # key -> (items, at)
        self.usage_path = Path(state_dir) / 'suggest-usage.jsonl'

    def config(self):
        return {'model': self.client is not None}

    def _static_block(self):
        with self._catalog_lock:
            cached = self._catalog
            if cached and time.monotonic() - cached[2] < CATALOG_TTL:
                return cached[0], cached[1]
        text, music_ids = _build_static_block(self.music)
        with self._catalog_lock:
            self._catalog = (text, music_ids, time.monotonic())
        return text, music_ids

    def _known(self, family, id_, music_ids):
        if family == 'looks':
            return id_ in self._looks_ids
        if family == 'type':
            return id_ in self._type_ids
        if family == 'capabilities':
            return id_ in self._cap_ids
        if family == 'fonts':
            return id_ in fonts_module.ids()
        if family == 'sfx':
            try:
                sfx_module.bank().get(id_)
                return True
            except (ValueError, sfx_module.SfxUnavailable):
                return False
        if family == 'music':
            return id_ in music_ids
        return False

    def _validate(self, answer, text, music_ids):
        raw = answer.get('items') if isinstance(answer, dict) else answer
        if not isinstance(raw, list):
            return []
        strong, related, seen = [], [], set()
        for raw_item in raw:
            if not isinstance(raw_item, dict):
                continue
            id_, family, strength = raw_item.get('id'), raw_item.get('family'), raw_item.get('strength')
            if not isinstance(id_, str) or not isinstance(family, str) or strength not in ('strong', 'related'):
                continue
            if not self._known(family, id_, music_ids):
                continue
            key = (family, id_)
            if key in seen:
                continue
            seen.add(key)
            why = raw_item.get('why')
            why = why[:MAX_WHY] if isinstance(why, str) else ''
            replace = raw_item.get('replace')
            valid_replace = None
            if isinstance(replace, dict):
                span, rtext = replace.get('span'), replace.get('text')
                if isinstance(span, str) and span and isinstance(rtext, str) and rtext and span in text:
                    valid_replace = {'span': span, 'text': rtext}
            item = {'id': id_, 'family': family, 'strength': strength, 'why': why, 'replace': valid_replace}
            (strong if strength == 'strong' else related).append(item)
        return strong[:STRONG_CAP] + related[:RELATED_CAP]

    def _cache_get(self, key):
        with self._answer_lock:
            entry = self._answers.get(key)
            if entry and time.monotonic() - entry[1] < ANSWER_TTL:
                return entry[0]
        return None

    def _cache_put(self, key, items):
        with self._answer_lock:
            self._answers[key] = (items, time.monotonic())
            if len(self._answers) > ANSWER_CACHE_MAX:
                oldest = min(self._answers, key=lambda k: self._answers[k][1])
                del self._answers[oldest]

    def _record_usage(self, author, usage):
        entry = {'author': author, 'at': time.time(),
                 'prompt_tokens': usage.get('prompt_tokens'), 'completion_tokens': usage.get('completion_tokens'),
                 'total_tokens': usage.get('total_tokens')}
        try:
            with open(self.usage_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry) + '\n')
        except OSError:
            pass

    def usage_totals(self):
        """{account: {calls, prompt_tokens, completion_tokens, total_tokens}},
        all-time, from the usage log -- there is no cap to enforce yet, so
        this is a plain running total, not windowed like note cost."""
        totals = {}
        try:
            text = self.usage_path.read_text(encoding='utf-8')
        except OSError:
            return totals
        for line in text.splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            account = _account_key(entry.get('author'), self.has_accounts) or 'anonymous'
            t = totals.setdefault(account, {'calls': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
                                            'total_tokens': 0})
            t['calls'] += 1
            for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                v = entry.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    t[k] += v
        return totals

    def ask(self, editor, video, body, author, cancel_event=None):
        """`editor` and `video` are both None for New video's "In a few
        words" (asked before any video exists, so there is no bible or
        timeline to read yet); otherwise `editor` is the specific project's
        Editor the note box belongs to.

        `cancel_event`, if given, is a `threading.Event` the caller may also
        set from outside (its own request socket closing) -- same event the
        timeout below arms, so either one stops the model call."""
        if self.client is None:
            raise HTTPError(404, 'not configured')
        text = body.get('text')
        if not isinstance(text, str):
            raise HTTPError(400, 'text must be a string')
        text = text.strip()
        surface = body.get('surface')
        if surface not in ('editor', 'new'):
            raise HTTPError(400, 'surface must be "editor" or "new"')
        clip = body.get('clip')
        if clip is not None and not isinstance(clip, str):
            raise HTTPError(400, 'clip must be a string')
        at = body.get('at')
        if at is not None and (isinstance(at, bool) or not isinstance(at, (int, float))):
            raise HTTPError(400, 'at must be a number')
        seq = body.get('seq')
        if isinstance(seq, bool) or not isinstance(seq, int):
            raise HTTPError(400, 'seq must be an integer')
        if video is not None:
            editor.project.video(video)
        if len(text.split()) < MIN_WORDS:
            return {'seq': seq, 'items': []}
        static_block, music_ids = self._static_block()
        # In library mode every project's Editor shares this one Suggest, and `video` is the
        # bare in-project name -- so without the project itself in the key, two projects with
        # the same video name and note would share an answer (and its why-text, drawn from the
        # first project's own bible) across accounts. `editor.state_dir` is unique per project.
        project_key = editor.state_dir if editor is not None else None
        cache_key = (self.client.model, len(static_block), project_key, video, clip, _normalize(text))
        cached = self._cache_get(cache_key)
        if cached is not None:
            return {'seq': seq, 'items': cached}
        video_block = _video_block(editor, video) if video is not None else NEW_VIDEO_BLOCK
        if cancel_event is None:
            cancel_event = threading.Event()
        timer = threading.Timer(self.client.timeout, cancel_event.set)
        timer.daemon = True
        timer.start()
        try:
            answer, usage = self.client.complete(static_block, video_block, _user_text(surface, clip, at, text),
                                                 cancel_event=cancel_event)
        except SuggestCancelled:
            if timer.finished.is_set():  # the timer fired; a browser that went away isn't worth a line
                print(f'[editor] suggest: no answer within {self.client.timeout:g}s', file=sys.stderr, flush=True)
            return {'seq': seq, 'items': []}
        except SuggestError as exc:
            print(f'[editor] suggest: {exc}', file=sys.stderr, flush=True)
            return {'seq': seq, 'items': []}
        finally:
            timer.cancel()
        items = self._validate(answer, text, music_ids)
        if not items:
            print(f'[editor] suggest: the model matched nothing usable: {json.dumps(answer)[:300]}',
                  file=sys.stderr, flush=True)
        self._cache_put(cache_key, items)
        if usage:
            self._record_usage(author, usage)
        return {'seq': seq, 'items': items}

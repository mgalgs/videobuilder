"""Capability suggestions while a director types a note: the model reads the
catalog, the film's bible and timeline, the selected clip and the typed
text, and answers which looks, type styles, fonts, sound effects, capabilities
and (where configured) music fit it -- see suggest_client.py for the model
call itself, and suggest-notes.md (the design round that specified this) for
the full picture.

The catalog the model sees is two system blocks. A small, cached one
(Looks, Type, Fonts, and one line per `capabilities.REGISTRY_FAMILIES`
family) lists what's cheap to list in full every time. Everything else --
every other capability (hundreds of them, read through
`videobuilder.capabilities.registry`),
every sound effect and every music track -- is far too large to list in
full without making a small model's choice vague and slow. Those are
matched per note instead, by a BM25 index (`suggest_index.py`) built over
the same lists, and the best few of each go into a second, per-note block
(`_shortlist_block`) alongside the bible/timeline block already there.

One `Suggest` exists wherever a model is configured (None otherwise, see
Editor.__init__/Library.__init__): it builds the two system blocks, asks the
client, validates every id it gets back against the real catalog/fonts/sfx
pack/music list (an id or a span that doesn't check out is dropped silently,
never shown), caps the answer, caches it briefly so retyping or undoing is
instant, and records token usage per account. Nothing here ever raises past
a bad request shape; a model failure just answers no items, because a note
box must never show the director an error for this.

Unlike Pictures (one per project, sharing only its Artbox client), nothing
in `Suggest` is project-specific: the catalog, the answer cache and the
usage log all make sense shared across a whole library. So one `Suggest`
is built once -- at the Library in library mode, at the Editor in
single-project mode -- and `ask()` takes whichever project's Editor the
request is for (None for New video's "In a few words", asked before any
video exists)."""
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

from . import fonts as fonts_module
from . import sfx as sfx_module
from .editor import HTTPError, _account_key
from .suggest_client import SuggestCancelled, SuggestError
from .suggest_index import BM25

NEW_VIDEO_BLOCK = '(There is no video yet: the director is describing a brand new one before it exists.)'

NAME_SYSTEM_BLOCK = (
    'You suggest a short name for a brand-new video project, from the director\'s idea, the names of any '
    'files they have attached, and (for songs) notes on what the song sounds like. Answer JSON only: '
    '{"name": "..."}. The name should read like a short slug a filesystem would accept -- a few words, '
    'lowercase, hyphens instead of spaces, no punctuation, 2-40 characters (e.g. "lighthouse-storm", '
    '"snow-day-reel") -- never a sentence, a quote, or a file extension.'
)
MAX_NAME_INPUT = 1500  # characters of idea text / file names / listening notes sent to the model
MAX_LISTENING_EXCERPT = 600

STRONG_CAP = 5
RELATED_CAP = 8
MIN_WORDS = 3
CATALOG_TTL = 600  # seconds: the static block and the per-note retrieval indices are rebuilt this often
ANSWER_TTL = 300  # 5 minutes, per the design notes
ANSWER_CACHE_MAX = 500
MAX_WHY = 200
MAX_BIBLE_CHARS = 4000
CAPABILITY_SHORTLIST = 30  # how many of each per-note retrieval answers, into the per-note block
SFX_SHORTLIST = 15
MUSIC_SHORTLIST = 10
_PUNCT_WS = re.compile(r'[\s,.;:!?]+')
DEFAULT_NOTES_FIXTURE = Path(__file__).resolve().parent.parent / 'tests' / 'fixtures' / 'suggest-notes.jsonl'


def _normalize(text):
    """Collapses whitespace/punctuation differences, so retyping or a pick's
    own rewrite doesn't look like a new question to the answer cache."""
    return _PUNCT_WS.sub(' ', text.strip().lower()).strip()


def _looks_and_type_ids():
    """(looks ids, type ids): the members of the Looks and Type
    capabilities -- never those grouping capabilities themselves ('looks',
    'type'), which aren't things a note can ask for."""
    from . import capabilities
    return (set(capabilities.get('looks').members.ids), set(capabilities.get('type').members.ids))


def _catalog_entry_line(t, family):
    prompts = ' / '.join(t.phrasings[:2])
    return f"{t.id} | {family} | {t.name} | {t.definition} | {prompts}"


def _build_static_block():
    """The static, cacheable system block: instructions, then Looks, Type
    and Fonts in full (small, curated lists, cheap to always list), then
    one line per `capabilities.REGISTRY_FAMILIES` family so the model
    knows what else exists. Every other capability, every sound effect and every
    music track is matched per note instead -- see `_build_indices` and
    `_shortlist_block` -- because listing hundreds of them here every time
    would make a small model's choice vague and slow."""
    from . import capabilities
    lines = ['You are the suggestion engine behind a video builder\'s note box. Given a short note from a '
             'director, suggest the looks, type styles, fonts, sound effects, music or other capabilities that '
             'fit what they are asking for, so they can pick one by name -- from the catalog below, and from '
             'the per-note block that follows it (this note\'s own best local matches from much larger lists '
             'of capabilities, sound effects and music). Whenever the note touches something either block '
             'covers -- a look or style, text or a font, a sound, music, a kind of motion -- answer with the '
             'best few of that kind (two to six), even when the note is vague ("change the look to something" '
             'gets several looks as "related"). Answer an empty list only when nothing in either block relates '
             'to the note. '
             'Never suggest something the bible or the note already names. Use "strong" only for a direct '
             'match; everything else related is "related". `span` must be the director\'s exact words (a '
             'substring of the note); `text` keeps their words and adds the unique name in plain words, e.g. '
             '"a friendlier font (Cantarell)" or "a whoosh (whoosh_fast/tight)". Answer JSON only: '
             '{"items": [{"id", "family" (one of looks/type/fonts/sfx/music/capabilities), "strength" '
             '("strong"|"related"), "why", "replace": {"span", "text"} or null}]}.',
             '', 'Catalog (id | family | title | card | example phrasings):']
    for family in ('looks', 'type'):  # every other capability is matched per note instead
        for t in capabilities.members(capabilities.get(family)):
            lines.append(_catalog_entry_line(t, family))
    lines.append('')
    lines.append('Fonts (id | family | about):')
    for f in fonts_module.public():
        lines.append(f"{f['id']} | {f['family']} | {f['about']}")
    lines.append('')
    lines.append('Capability families (hundreds more capabilities than listed above, grouped; the per-note '
                 'block carries this note\'s own best matches from them):')
    for fam, (title, description) in capabilities.REGISTRY_FAMILIES.items():
        lines.append(f'{fam} | {title} | {description}')
    return '\n'.join(lines)


def _capability_line(entry):
    """One retrieval-block line, in the static block's own format (id |
    capabilities | title | card | example phrasings), for a capability record."""
    return _catalog_entry_line(entry, 'capabilities')


def _capability_entry(id_):
    """The capability named `id_` (an old id included). KeyError if there is
    none (never happens for an id the index itself just handed back)."""
    from . import capabilities
    return capabilities.get(id_)


def _capability_docs():
    """Every capability's retrieval text (apart from the Looks and Type
    members, which stay in the static block, and the capabilities that
    group them), all answering with family "capabilities": one with a card
    of its own by its name, aliases, card line, description, phrasings and
    page section; every other one by its name, aliases, phrasings,
    definition, group and family."""
    from . import capabilities
    from .capabilities import registry
    looks, type_ = _looks_and_type_ids()
    static = looks | type_ | {'looks', 'type'}
    docs = []
    for t in capabilities.cards():
        if t.id in static:
            continue  # a look/type member (stays in the static block), or the capability grouping them
        docs.append((t.id, ' '.join((t.name, *t.aliases, t.definition, t.description, *t.phrasings, t.category))))
    for t in registry.catalog():
        if not capabilities.has_card(t):
            docs.append((t.id, ' '.join((t.name, *t.aliases, *t.phrasings, t.definition, t.group, t.family))))
    return docs


def _sfx_docs():
    docs = []
    try:
        for effect in sfx_module.bank().find():
            docs.append((effect.id, ' '.join((effect.id, effect.role, effect.family, effect.about))))
    except sfx_module.SfxUnavailable:
        pass
    return docs


def _music_docs(music):
    """([(id, text), ...], {id: track}) -- best-effort: a source that can't
    be fetched right now is skipped rather than failing the whole index."""
    docs, by_id = [], {}
    if music:
        for source in music.list_sources():
            try:
                _, tracks = music.list_tracks(source['id'])
            except Exception:
                continue
            for t in tracks:
                by_id[t['id']] = t
                docs.append((t['id'], ' '.join((t['title'], *t.get('tags', ())))))
    return docs, by_id


def _build_indices(music):
    """The per-note retrieval indices, rebuilt on the same schedule as the
    static block: one BM25 index each for capabilities, sound effects and
    music tracks (plus `music_by_id`, for formatting a shortlisted track's
    line and for validating a music id later)."""
    music_docs, music_by_id = _music_docs(music)
    return BM25(_capability_docs()), BM25(_sfx_docs()), BM25(music_docs), music_by_id


def _shortlist_block(capability_index, sfx_index, music_index, music_by_id, query_text):
    """The per-note system block: this note's own best local matches from
    the three retrieval indices, in the static block's own line formats.
    An empty string when nothing in any index matches."""
    lines = []
    cap_ids = capability_index.query(query_text, CAPABILITY_SHORTLIST)
    if cap_ids:
        lines.append('Capabilities (id | family | title | card | example phrasings):')
        lines += [_capability_line(_capability_entry(id_)) for id_ in cap_ids]
        lines.append('')
    sfx_ids = sfx_index.query(query_text, SFX_SHORTLIST)
    if sfx_ids:
        lines.append('Sound effects (id | role | family | about):')
        for id_ in sfx_ids:
            effect = sfx_module.bank().get(id_)
            lines.append(f'{effect.id} | {effect.role} | {effect.family} | {effect.about}')
        lines.append('')
    track_ids = music_index.query(query_text, MUSIC_SHORTLIST)
    if track_ids:
        lines.append('Music (id | title | tags):')
        for id_ in track_ids:
            t = music_by_id[id_]
            lines.append(f"{id_} | {t['title']} | {', '.join(t.get('tags', ()))}")
    if not lines:
        return ''
    return '\n'.join(["This note's own best local matches from the much larger capabilities, sound-effect and "
                      'music lists (not the full lists, which are too many for every prompt):', '', *lines]).rstrip()


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
        self._looks_ids, self._type_ids = _looks_and_type_ids()
        self._catalog_lock = threading.Lock()
        self._catalog = None  # (text, capability_index, capability_ids, sfx_index, music_index, music_ids,
                               #  music_by_id, built_at)
        self._answer_lock = threading.Lock()
        self._answers = {}  # key -> (items, at)
        self.usage_path = Path(state_dir) / 'suggest-usage.jsonl'

    def config(self):
        return {'model': self.client is not None}

    def _static_block(self):
        with self._catalog_lock:
            cached = self._catalog
            if cached and time.monotonic() - cached[-1] < CATALOG_TTL:
                return cached[:-1]
        text = _build_static_block()
        capability_index, sfx_index, music_index, music_by_id = _build_indices(self.music)
        bundle = (text, capability_index, frozenset(capability_index.ids), sfx_index, music_index,
                 frozenset(music_by_id), music_by_id)
        with self._catalog_lock:
            self._catalog = bundle + (time.monotonic(),)
        return bundle

    def _known(self, family, id_, capability_ids, music_ids):
        if family == 'looks':
            return id_ in self._looks_ids
        if family == 'type':
            return id_ in self._type_ids
        if family == 'capabilities':
            return id_ in capability_ids
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

    def _validate(self, answer, text, capability_ids, music_ids):
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
            if not self._known(family, id_, capability_ids, music_ids):
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

    def ask(self, editor, video, body, author, cancel_event=None, on_error=None):
        """`editor` and `video` are both None for New video's "In a few
        words" (asked before any video exists, so there is no bible or
        timeline to read yet); otherwise `editor` is the specific project's
        Editor the note box belongs to.

        `cancel_event`, if given, is a `threading.Event` the caller may also
        set from outside (its own request socket closing) -- same event the
        timeout below arms, so either one stops the model call.

        `on_error`, if given, is called with a short string whenever the
        model call itself failed (timeout or `SuggestError`) rather than
        just matching nothing -- `run_eval` uses this to tell "the model
        was bad" apart from "the model was never reached", which an empty
        `items` list can't say on its own. The note box itself never passes
        this: a model failure must still just answer no items, never an
        error."""
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
        (static_block, capability_index, capability_ids, sfx_index, music_index,
         music_ids, music_by_id) = self._static_block()
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
        query_text = f'{text} {clip}' if clip else text
        shortlist_block = _shortlist_block(capability_index, sfx_index, music_index, music_by_id, query_text)
        if shortlist_block:
            video_block = f'{video_block}\n\n{shortlist_block}'
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
                msg = f'no answer within {self.client.timeout:g}s'
                print(f'[editor] suggest: {msg}', file=sys.stderr, flush=True)
                if on_error:
                    on_error(msg)
            return {'seq': seq, 'items': []}
        except SuggestError as exc:
            print(f'[editor] suggest: {exc}', file=sys.stderr, flush=True)
            if on_error:
                on_error(str(exc))
            return {'seq': seq, 'items': []}
        finally:
            timer.cancel()
        items = self._validate(answer, text, capability_ids, music_ids)
        if not items:
            print(f'[editor] suggest: the model matched nothing usable: {json.dumps(answer)[:300]}',
                  file=sys.stderr, flush=True)
        self._cache_put(cache_key, items)
        if usage:
            self._record_usage(author, usage)
        return {'seq': seq, 'items': items}

    def suggest_name(self, idea, file_names, listening_notes, author, cancel_event=None):
        """{"name": "..."} for New video's Suggest button: a short slug
        drawn from the idea text, the names of whatever's been staged, and
        -- for songs the listening cache already has notes for --
        `listening_notes` ({file name: notes text}). `name` is None (never
        an error) when there's nothing to go on yet, the model isn't
        configured, or the call fails -- the page keeps today's name field
        either way. The caller still runs the answer through the same name
        validation any typed name gets; nothing here is trusted as final."""
        if self.client is None:
            raise HTTPError(404, 'not configured')
        idea = (idea or '').strip()
        if not idea and not file_names:
            return {'name': None}
        lines = []
        if idea:
            lines.append(f'Idea: {idea[:MAX_NAME_INPUT]}')
        if file_names:
            lines.append('Files: ' + ', '.join(file_names[:50]))
        for name, notes in listening_notes.items():
            lines.append(f'Notes on {name}:\n{notes[:MAX_LISTENING_EXCERPT]}')
        user_text = '\n\n'.join(lines)[:MAX_NAME_INPUT]
        cache_key = ('name', self.client.model, _normalize(user_text))
        cached = self._cache_get(cache_key)
        # '' (not None) marks a cached miss -- a cache lookup answering plain None always
        # means "not cached", so a real miss has to be stored as something else or it would
        # look uncached forever and re-ask the model every time.
        if cached is not None:
            return {'name': cached or None}
        if cancel_event is None:
            cancel_event = threading.Event()
        timer = threading.Timer(self.client.timeout, cancel_event.set)
        timer.daemon = True
        timer.start()
        try:
            answer, usage = self.client.complete(NAME_SYSTEM_BLOCK, NEW_VIDEO_BLOCK, user_text, max_tokens=40,
                                                 cancel_event=cancel_event)
        except (SuggestCancelled, SuggestError) as exc:
            if not isinstance(exc, SuggestCancelled) or timer.finished.is_set():
                print(f'[editor] suggest name: {exc}', file=sys.stderr, flush=True)
            return {'name': None}
        finally:
            timer.cancel()
        name = answer.get('name') if isinstance(answer, dict) else None
        name = name.strip().strip('"\'')[:80] if isinstance(name, str) else None
        self._cache_put(cache_key, name or '')
        if usage:
            self._record_usage(author, usage)
        return {'name': name or None}


def _load_notes(path):
    notes = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                notes.append(json.loads(line))
    return notes


def run_eval(notes_path, suggest_url, suggest_model):
    """`python -m videobuilder suggest eval`: the full suggest path --
    retrieval plus the configured model, never a fake -- over a fixture of
    notes (`tests/fixtures/suggest-notes.jsonl` by default), printing each
    note's strong and related picks and whether a good id was among them,
    then a final hit rate. Raises SystemExit, cleanly and without a
    traceback, when no model is configured (no `--suggest-url`, or
    $VIDEOBUILDER_SUGGEST_KEY unset) -- some environments this runs in have
    no network, and a bad config must say so plainly rather than crash."""
    import tempfile
    from .suggest_client import SuggestClient
    key = os.environ.get('VIDEOBUILDER_SUGGEST_KEY')
    if not suggest_url or not key:
        raise SystemExit('suggest eval needs --suggest-url and $VIDEOBUILDER_SUGGEST_KEY set; no model is '
                         'configured')
    notes = _load_notes(notes_path or DEFAULT_NOTES_FIXTURE)
    client = SuggestClient(suggest_url, suggest_model, key)
    hits = 0
    errors = []  # one entry per note whose model call itself failed, not just matched nothing
    with tempfile.TemporaryDirectory() as state_dir:
        suggest = Suggest(state_dir, client)
        for i, note in enumerate(notes, 1):
            body = {'text': note['note'], 'surface': 'new', 'clip': note.get('clip'), 'at': None, 'seq': i}
            note_errors = []
            result = suggest.ask(None, None, body, 'eval', on_error=note_errors.append)
            errors += note_errors
            items = result['items']
            strong = [it['id'] for it in items if it['strength'] == 'strong']
            related = [it['id'] for it in items if it['strength'] == 'related']
            good = set(note.get('good', ()))
            hit = bool(good & {it['id'] for it in items})
            hits += hit
            print(f"{i}. {note['note']!r}")
            if note_errors:
                print(f'   model error: {note_errors[0]}')
            print(f'   strong: {strong}')
            print(f'   related: {related}')
            print(f"   {'hit' if hit else 'miss'} (good: {sorted(good)})")
    rate = hits / len(notes) if notes else 0.0
    print(f'{hits}/{len(notes)} ({rate:.0%}) hit rate')
    if errors:
        print(f'{len(errors)}/{len(notes)} note(s) got a model error rather than an answer -- '
             'the hit rate above undercounts them')
    if notes and len(errors) == len(notes):
        raise SystemExit(f'the model failed on every note ({errors[0]!r}); nothing was measured')

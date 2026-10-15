"""Review notes: a reviewer's request pinned to a moment of a video, for an
agent to act on. The editor stores them; an `AgentBackend` takes them on.

A note pins its text to (video, format, frame, segment) and keeps that
frame's PNG beside it. Notes live in the editor's state directory, one JSON
file and one PNG per note:

    <state>/notes/<id>.json
    <state>/notes/<id>.png

The backend retains submit(note) -> str and poll(handle) -> AgentStatus.
Submissions additionally carry project, film, directory, beat, time, image,
note_file, state_dir, session (stable id), and draft (current branch or null).
One note per video is submitted at a time; other notes wait in order.
Listing notes polls in-flight handles, including after restart, and dispatches
the next note after replied/failed. accepted/dropped are reviewer decisions.
Per-video session.json survives both decisions. The runner owns any additional
session files. See agents.py for the external command protocol. Submission
must be idempotent by note id to tolerate a crash before saving the handle.

A reply that carries a ```questions fenced JSON block (see
parse_questions) lands the note in the `questions` state instead of `replied`,
with the parsed list in note['questions'] and any lead-in text as its reply.
A builder that asked is told to commit nothing, so ordinarily no version is
produced; if it committed anyway, those commits land right away exactly as an
ordinary reply's would, and the note keeps its `questions` for display. `answer()`
turns the note into a follow-up note that continues the same draft and is marked
not to ask again.

A reply may also carry a ```shortfalls fenced JSON block (see strip_shortfalls),
naming a request the builder could not do at all or could not do well. It is
stripped from the reply either way -- the creator must never see raw JSON -- and,
when valid, stored as note['shortfalls']: a plain note field, so it reaches
clients through the existing notes API with no route changes.

A poll's `AgentStatus` may also carry `cost_usd` (a number) and `tokens` (an
object), whatever the backend reported for that run; both default to None
and stay None when a backend never reports them -- never estimated, and
never coerced to zero, so "unknown" stays distinguishable from "free". Each
poll's status fields are copied onto the note as-is, so a note's cost and
token counts are exactly what the last poll reported.
"""
import hashlib
from pathlib import Path
import json
import os
import re
import secrets
import threading
import time
from dataclasses import asdict, dataclass

from .atomic import write_json_atomic
from . import prompt

STATES = ('gathering', 'queued', 'working', 'replied', 'failed', 'accepted', 'dropped', 'landed', 'refused',
         'conflict', 'questions')
FINAL = ('replied', 'failed', 'accepted', 'dropped', 'landed', 'refused', 'conflict', 'questions')

QUESTIONS_MAX = 3
CHOICES_MIN, CHOICES_MAX = 2, 4
TEXT_MAX = 200
CHOICE_MAX = 60
LEAD_IN_MAX = 300

SHORTFALL_KINDS = ('cannot', 'weak')
SHORTFALLS_MAX = 5
WHAT_MAX = 160

# The whole /attachments directory a submission mounts for the builder -- attachments,
# pinned frame and source-video previews together -- stays under this; fork-sandbox's
# k8s push tars that directory and refuses one over 256 MiB, so this leaves headroom.
ATTACH_DIR_BUDGET = 200 * 1048576

# The crawl's own cap is about two minutes (gather.TIME_BUDGET); a `gathering` note
# older than this had its background thread die before finishing -- an editor
# restart, redeploy or crash -- and is recovered rather than left stuck forever.
GATHER_STALE_SECONDS = 10 * 60


def parse_questions(reply):
    """A builder reply's last ```questions fenced block, strictly
    validated: (lead_in, questions), each question a dict `text` plus
    `choices` (empty for free text, else 2-4 short strings), or None for a
    missing or malformed block, which is then an ordinary reply."""
    if not reply:
        return None
    # The last block wins, and text after it (a habitual Summary line) is dropped:
    # a model that strays from "nothing after the block" must not leak raw JSON.
    matches = list(re.finditer(r'```questions[ \t]*\r?\n(.*?)\r?\n```[ \t]*(?:\r?\n|\Z)', reply, re.S))
    if not matches:
        return None
    m = matches[-1]
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get('questions'), list):
        return None
    questions = data['questions']
    if not 1 <= len(questions) <= QUESTIONS_MAX:
        return None
    parsed = []
    for q in questions:
        if not isinstance(q, dict):
            return None
        text = q.get('text')
        if not isinstance(text, str) or not text.strip() or len(text) > TEXT_MAX:
            return None
        choices = q.get('choices') or []
        if not isinstance(choices, list):
            return None
        if choices:
            if not CHOICES_MIN <= len(choices) <= CHOICES_MAX:
                return None
            if not all(isinstance(c, str) and c.strip() and len(c) <= CHOICE_MAX for c in choices):
                return None
        parsed.append({'text': text.strip(), 'choices': [c.strip() for c in choices]})
    lead_in = reply[:m.start()].strip()[:LEAD_IN_MAX]
    return lead_in, parsed


def strip_shortfalls(reply):
    """A builder reply's last ```shortfalls fenced block: the reply with that
    block removed, plus the parsed list of {kind, what} it held, or None for a
    missing or malformed block. Validated strictly, in the same style as
    parse_questions: kind is 'cannot' or 'weak', what is a short plain-language
    phrase (1-160 characters), 1-5 entries. The block is stripped either way --
    malformed JSON must never reach the creator -- but a malformed or absent
    block records nothing."""
    if not reply:
        return reply, None
    # The body may not span a fence: an unclosed block must not swallow a following
    # ```questions block and lose the builder's questions.
    matches = list(re.finditer(r'```shortfalls[ \t]*\r?\n((?:(?!```).)*?)\r?\n```[ \t]*(?:\r?\n|\Z)',
                               reply, re.S))
    if not matches:
        return reply, None
    m = matches[-1]
    # Collapse the blank-line seam the excision leaves behind, so a stripped block
    # never shows up to the creator as a stray run of empty lines.
    cleaned = re.sub(r'\n{3,}', '\n\n', reply[:m.start()] + reply[m.end():]).strip('\n')
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return cleaned, None
    if not isinstance(data, dict) or not isinstance(data.get('shortfalls'), list):
        return cleaned, None
    items = data['shortfalls']
    if not 1 <= len(items) <= SHORTFALLS_MAX:
        return cleaned, None
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            return cleaned, None
        kind, what = item.get('kind'), item.get('what')
        if kind not in SHORTFALL_KINDS:
            return cleaned, None
        if not isinstance(what, str) or not what.strip() or len(what) > WHAT_MAX:
            return cleaned, None
        parsed.append({'kind': kind, 'what': what.strip()})
    return cleaned, parsed


@dataclass
class AgentStatus:
    state: str                 # one of STATES
    reply: str | None = None   # the agent's answer to the reviewer
    branch: str | None = None  # a draft branch with the agent's change, for review
    cost_usd: float | None = None  # what this run cost, or None when the backend didn't report it
    tokens: dict | None = None     # token counts as the backend reported them, or None

    def __post_init__(self):
        if self.state not in STATES:
            raise ValueError(f'unknown note state {self.state!r}; known: {", ".join(STATES)}')
        if self.cost_usd is not None and (isinstance(self.cost_usd, bool) or not isinstance(self.cost_usd, (int, float))):
            raise ValueError('cost_usd must be a number or null')
        if self.tokens is not None and not isinstance(self.tokens, dict):
            raise ValueError('tokens must be an object or null')


class AgentBackend:
    """Where notes go. Subclass it, and pass an instance to the editor."""
    name = 'agent'

    def submit(self, note):
        """Take on `note` (a dict: id, video, format, frame, segment, text,
        author, created, and `image`, the path of its frame's PNG). Return a
        handle (a string) to poll it by. Called once per note."""
        raise NotImplementedError

    def poll(self, handle):
        """The `AgentStatus` of the note submitted as `handle`."""
        raise NotImplementedError


class NullBackend(AgentBackend):
    """Sends notes nowhere: every note stays queued."""
    name = 'null'

    def submit(self, note):
        return f'null:{note["id"]}'

    def poll(self, handle):
        return AgentStatus('queued')


class NoteStore:
    """Notes on disk under `dir`, submitted to `backend` as they are added."""

    def __init__(self, dir, backend=None, context=None, before_submit=None, on_reply=None, attachments=None,
                compendium_for_builder=False, compendium_votes=None):
        self.dir = os.path.abspath(dir)
        self.backend = backend or NullBackend()
        self.lock = threading.RLock()
        self.video_locks = {}
        self.context = context or (lambda video: {})
        self.before_submit, self.on_reply, self.attachments = before_submit, on_reply, attachments
        self.sources = None  # set by Editor.__init__ once editor.sources exists
        # compendium_for_builder is the [editor] kill switch for the bake-off (see
        # prompt._compendium_lines); compendium_votes, when set, is a zero-arg callable
        # returning {id: "up"|"down"} (see CompendiumVotes.current).
        self.compendium_for_builder, self.compendium_votes = compendium_for_builder, compendium_votes

    def video_lock(self, video):
        with self.lock:
            return self.video_locks.setdefault(video, threading.RLock())

    def _path(self, nid, ext):
        if not nid or not all(c.isalnum() or c in '-_' for c in nid):
            raise KeyError(nid)
        return os.path.join(self.dir, f'{nid}.{ext}')

    def _save(self, note):
        write_json_atomic(self._path(note['id'], 'json'), note, newline=True, indent=1, ensure_ascii=False)

    def update(self, note, **changes):
        """The one public way to change a stored note: applies `changes` to `note`
        in place and persists it, holding its video's lock as every internal
        mutation does."""
        with self.video_lock(note['video']):
            note.update(**changes)
            self._save(note)
        return note

    def add(self, video, format, frame, segment, text, png, author=None, **context):
        """Store a new note with its frame's PNG bytes, submit it, and return it."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError('a note needs some text')
        os.makedirs(self.dir, exist_ok=True)
        now = time.time()
        nid = time.strftime('%Y%m%dT%H%M%S', time.gmtime(now)) + f'{int(now % 1 * 1e6):06d}Z-{secrets.token_hex(3)}'
        if png is not None:
            with open(self._path(nid, 'png'), 'wb') as fh:
                fh.write(png)
        note = {'id': nid, 'video': video, 'format': format, 'frame': frame, 'segment': segment,
                'text': text.strip(), 'author': author,
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
                **context, 'backend': self.backend.name, 'handle': None, **asdict(AgentStatus('queued'))}
        with self.video_lock(video):
            self._save(note)
            self._advance(video)
            note = self.get(nid)
        return note

    def start_gathering(self, video, format, text=None, author=None, attachments=None, **context):
        """A placeholder note in the `gathering` state, saved and visible to
        every viewer (reload, another device, loadNotes' poll) before the
        gatherer -- which can run for up to about two minutes -- has
        produced the first note's real text. `_advance` stops at a
        `gathering` note the same way it stops at an in-flight one, so a
        note added while the brief is gathering waits for it rather than
        being submitted first; `finish_gathering` supplies the real text
        and moves it to `queued`, where `_advance` submits it as usual."""
        os.makedirs(self.dir, exist_ok=True)
        now = time.time()
        nid = time.strftime('%Y%m%dT%H%M%S', time.gmtime(now)) + f'{int(now % 1 * 1e6):06d}Z-{secrets.token_hex(3)}'
        note = {'id': nid, 'video': video, 'format': format, 'frame': None, 'segment': None,
                'text': (text or '').strip() or 'Starting this video…', 'author': author,
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)), 'gather_started': now,
                'attachments': attachments or [], **context, 'backend': self.backend.name, 'handle': None,
                **asdict(AgentStatus('gathering'))}
        with self.video_lock(video):
            self._save(note)
            note = self.get(nid)
        return note

    def finish_gathering(self, nid, text, attachments):
        """Supply a `gathering` note's real text and attachments once the
        gatherer finishes, and move it to `queued` so `_advance` submits it."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError('a note needs some text')
        video = self.get(nid)['video']
        with self.video_lock(video):
            note = self.get(nid)
            if note['state'] != 'gathering':
                # _advance already gave up on this crawl as stale and sent the note on.
                return note
            note.update(text=text.strip(), attachments=attachments, **asdict(AgentStatus('queued')))
            self._save(note)
            self._advance(video)
            note = self.get(nid)
        return note

    def get(self, nid):
        try:
            with open(self._path(nid, 'json'), encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            raise KeyError(nid) from None

    def current(self, nid):
        """One note after polling its video's backend, as list() does."""
        video = self.get(nid)['video']
        with self.video_lock(video):
            self._advance(video)
        return self.get(nid)

    def image(self, nid):
        """The PNG bytes of a note's frame."""
        try:
            with open(self._path(nid, 'png'), 'rb') as fh:
                return fh.read()
        except FileNotFoundError:
            raise KeyError(nid) from None

    def session_dir(self, video):
        slug = ''.join(c if c.isascii() and c.isalnum() else '-' for c in video)
        slug = slug[:96]
        slug += '-' + hashlib.sha256(video.encode()).hexdigest()[:12]
        path = Path(self.dir).parent / 'sessions' / slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def session(self, video):
        path = self.session_dir(video) / 'session.json'
        if path.exists():
            return json.loads(path.read_text())
        state = dict(session=path.parent.name, draft=None)
        self.save_session(video, state)
        return state

    def save_session(self, video, state):
        write_json_atomic(self.session_dir(video) / 'session.json', state)

    def list(self, video=None, refresh=True):
        notes = []
        for path in sorted(Path(self.dir).glob('*.json')):
            try:
                note = self.get(path.stem)
            except KeyError:
                continue
            if video is None or note['video'] == video:
                notes.append(note)
        if refresh:
            for vid in dict.fromkeys(n['video'] for n in notes):
                with self.video_lock(vid):
                    self._advance(vid)
            return self.list(video, refresh=False)
        return notes

    def pending(self):
        """The videos that have a note not yet in a final state."""
        return list(dict.fromkeys(n['video'] for n in self.list(refresh=False) if n['state'] not in FINAL))

    def tick(self):
        """Advance every video with unfinished notes, as a page poll would."""
        for vid in self.pending():
            with self.video_lock(vid):
                self._advance(vid)

    def _advance(self, video):
        for note in self.list(video, refresh=False):
            if note['state'] in FINAL:
                continue
            if note['state'] == 'gathering':
                if time.time() - note.get('gather_started', 0) <= GATHER_STALE_SECONDS:
                    # Still being filled in by the background crawl: stop here, the same
                    # way an in-flight note blocks the rest, so a note added while the
                    # brief is gathering waits for it instead of jumping the queue.
                    return
                # The thread that was going to call finish_gathering is gone (the
                # editor restarted, redeployed or crashed mid-crawl): queue the note
                # as-is rather than leaving this video blocked forever.
                note['text'] = (note['text'].strip() + '\n\nSome pages were not gathered: the crawl was '
                                'interrupted (likely an editor restart) before it finished.').strip()
                note.update(**asdict(AgentStatus('queued')))
                self._save(note)
            state = self.session(video)
            if not note['handle']:
                if self._submit(video, note, state):
                    return
            else:
                if self._poll(video, note, state):
                    return
            self._save(note)
            if note['state'] not in FINAL:
                return

    def _submit(self, video, note, state):
        """Build the prompt and hand `note` to the backend. True if submitted,
        telling `_advance` to stop for this tick (as the original `return` inside
        this block's try did); False to fall through to `_advance`'s common
        save-and-check-final tail (a submission failure is itself final)."""
        try:
            if self.before_submit:
                self.before_submit(video, note, state)
            payload = {**note, **self.context(video), **state,
                       'state_dir': str(self.session_dir(video)),
                       'image': self._path(note['id'], 'png') if note.get('frame') is not None else None}
            path = self.session_dir(video) / (note['id'] + '.md')
            # The runner sees the frame only through /attachments, never at its editor path.
            image = payload['image'] if payload['image'] and os.path.isfile(payload['image']) else None
            sources = self.sources.list(video) if self.sources else []
            any_ready = any(s.get('preview_ready') for s in sources)
            if self.attachments:
                payload['attach_dir'] = self.attachments.stage(note, image, force=any_ready)
                if image:
                    from .attachments import FRAME_NAME
                    image = '/attachments/' + FRAME_NAME
            if sources and payload.get('attach_dir'):
                attach_dir = Path(payload['attach_dir'])
                used = sum(f.stat().st_size for f in attach_dir.rglob('*') if f.is_file())
                in_sandbox = self.sources.stage_for_builder(video, attach_dir, max(0, ATTACH_DIR_BUDGET - used))
                sources = [{**s, 'in_sandbox': s['name'] in in_sandbox} for s in sources]
            compendium_source = getattr(self.backend, 'compendium_source', None) if self.compendium_for_builder else None
            compendium = bool(compendium_source(payload)) if compendium_source else False
            votes = self.compendium_votes() if compendium and self.compendium_votes else None
            path.write_text(prompt.render(note, payload, image, compendium=compendium, votes=votes,
                                          sources=sources), encoding='utf-8')
            payload['note_file'] = str(path)
            note['handle'] = self.backend.submit(payload)
            note['started'] = time.time()
            self._save(note)
            return True
        except Exception as e:
            note.update(state='failed', reply=f'could not submit: {e}')
            return False

    def _poll(self, video, note, state):
        """Poll the backend for `note`'s in-flight handle. True on a poll error,
        telling `_advance` to stop for this tick (as the original `return` in
        this block's except did); False otherwise, falling through to
        `_advance`'s common tail."""
        try:
            status = self.backend.poll(note['handle'])
            if status.branch and state['draft'] and status.branch != state['draft']:
                status = AgentStatus('failed', 'Runner returned a different draft branch; '
                                     'continue ' + state['draft'])
            shortfalls = None
            if status.state == 'replied':
                # Strip before parse_questions: the shortfalls block sits before the
                # questions block, so it would otherwise end up inside the lead-in text.
                reply, shortfalls = strip_shortfalls(status.reply)
                status = AgentStatus(status.state, reply, status.branch, status.cost_usd, status.tokens)
            parsed = parse_questions(status.reply) if status.state == 'replied' else None
            if parsed:
                # Strip the raw block from what's shown even when asking is disabled: a backend
                # that ignores the no-questions instruction must not leak it into the reply.
                lead_in, questions = parsed
                if note.get('no_questions') or note.get('automatic'):
                    status = AgentStatus('replied', lead_in or None, status.branch, status.cost_usd, status.tokens)
                else:
                    note['questions'] = questions
                    status = AgentStatus('questions', lead_in or None, status.branch, status.cost_usd, status.tokens)
            if shortfalls:
                note['shortfalls'] = shortfalls
            note.update(asdict(status))
            note.pop('poll_error', None)
            if status.branch:
                state['draft'] = status.branch
                self.save_session(video, state)
            self._save(note)
            # A run that asked but committed anyway still lands those commits right away,
            # exactly as an ordinary reply would; the questions stay on the note for display.
            if self.on_reply and (status.state == 'replied'
                                   or (status.state == 'questions' and status.branch)):
                self.on_reply(video, note)
            return False
        except Exception as e:
            note['poll_error'] = str(e)
            self._save(note)
            return True

    def resolve(self, video, branch, action, author):
        with self.video_lock(video):
            for note in self.list(video, refresh=False):
                if note['branch'] == branch and note['state'] == 'replied':
                    note['state'] = action
                    note.setdefault('history', []).append(dict(state=action, author=author, at=time.time()))
                    self._save(note)
            state = self.session(video)
            state['draft'] = None
            self.save_session(video, state)

    def retry(self, nid, author=None):
        """Queue a conflicted or failed note again, as a new note that starts from
        main. The session's draft is cleared: it is the branch that went wrong."""
        video = self.get(nid)['video']
        with self.video_lock(video):
            note = self.get(nid)
            if note['state'] not in ('conflict', 'failed') or note.get('automatic'):
                raise ValueError('only a conflicted or failed note can be retried')
            if note.get('retried'):
                raise ValueError(f'note already retried as {note["retried"]}')
            if any(n['state'] not in FINAL for n in self.list(video, refresh=False)):
                raise ValueError('wait for queued and working notes before retrying')
            state = self.session(video)
            state['draft'] = None
            state.pop('rejection', None)
            self.save_session(video, state)
            png = self.image(nid) if note.get('frame') is not None else None
            context = {k: note[k] for k in ('time', 'beat', 'attachments', 'no_questions') if k in note}
            new = self.add(video, note['format'], note['frame'], note['segment'], note['text'], png,
                           author=author or note.get('author'), retried_from=nid, **context)
            note['retried'] = new['id']
            self._save(note)
            return new

    def answer(self, nid, build, answers, author=None):
        """Create a follow-up note from a note waiting on questions: built with
        the director's `answers` (one string per question, in order) or, when
        `build` is true, on the builder's best judgement. Continues the same
        draft (nothing went wrong, unlike retry) and is marked not to ask
        again."""
        video = self.get(nid)['video']
        with self.video_lock(video):
            note = self.get(nid)
            if note['state'] != 'questions':
                raise ValueError('note is not waiting on questions')
            if note.get('answered'):
                raise ValueError(f'note already answered as {note["answered"]}')
            if build:
                text = note['text'] + '\n\nBuild it with your best judgement; do not ask questions.'
            else:
                questions = note.get('questions') or []
                if (not isinstance(answers, list) or len(answers) != len(questions)
                        or not all(isinstance(a, str) and a.strip() for a in answers)):
                    raise ValueError('answers must be a nonempty string per question')
                parts = [note['text']]
                parts += [f"Q: {q['text']}\nA: {a.strip()}" for q, a in zip(questions, answers)]
                text = '\n\n'.join(parts)
            png = self.image(nid) if note.get('frame') is not None else None
            context = {k: note[k] for k in ('time', 'beat', 'attachments') if k in note}
            new = self.add(video, note['format'], note['frame'], note['segment'], text, png,
                           author=author or note.get('author'), answered_from=nid, no_questions=True, **context)
            note['answered'] = new['id']
            # Recorded here, not reconstructed from the follow-up's text later: that text is free-form
            # (the original note's own words may coincidentally match) and the follow-up can be deleted.
            note['answered_build'] = bool(build)
            if not build:
                note['answered_answers'] = [a.strip() for a in answers]
            self._save(note)
            return new

    def delete(self, nid):
        video = self.get(nid)['video']
        with self.video_lock(video):
            note = self.get(nid)
            if note['state'] not in FINAL and note['handle'] and self.backend.name != 'null':
                raise ValueError('cannot delete an in-flight note')
            for ext in ('json', 'png'):
                try:
                    os.remove(self._path(nid, ext))
                except FileNotFoundError:
                    pass

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

from .atomic import write_atomic, write_json_atomic

STATES = ('gathering', 'queued', 'working', 'replied', 'failed', 'accepted', 'dropped', 'landed', 'refused',
         'conflict', 'questions')
FINAL = ('replied', 'failed', 'accepted', 'dropped', 'landed', 'refused', 'conflict', 'questions')

QUESTIONS_MAX = 3
CHOICES_MIN, CHOICES_MAX = 2, 4
TEXT_MAX = 200
CHOICE_MAX = 60
LEAD_IN_MAX = 300

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


@dataclass
class AgentStatus:
    state: str                 # one of STATES
    reply: str | None = None   # the agent's answer to the reviewer
    branch: str | None = None  # a draft branch with the agent's change, for review

    def __post_init__(self):
        if self.state not in STATES:
            raise ValueError(f'unknown note state {self.state!r}; known: {", ".join(STATES)}')


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

    def __init__(self, dir, backend=None, context=None, before_submit=None, on_reply=None, attachments=None):
        self.dir = os.path.abspath(dir)
        self.backend = backend or NullBackend()
        self.lock = threading.RLock()
        self.video_locks = {}
        self.context = context or (lambda video: {})
        self.before_submit, self.on_reply, self.attachments = before_submit, on_reply, attachments

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
                try:
                    if self.before_submit:
                        self.before_submit(video, note, state)
                    payload = {**note, **self.context(video), **state,
                               'state_dir': str(self.session_dir(video)),
                               'image': self._path(note['id'], 'png') if note.get('frame') is not None else None}
                    path = self.session_dir(video) / (note['id'] + '.md')
                    # The runner sees the frame only through /attachments, never at its editor path.
                    image = payload['image'] if payload['image'] and os.path.isfile(payload['image']) else None
                    if self.attachments:
                        payload['attach_dir'] = self.attachments.stage(note, image)
                        if image:
                            from .attachments import FRAME_NAME
                            image = '/attachments/' + FRAME_NAME
                    lines = ['# Review request', '', *([note['rejection']] if note.get('rejection') else []), note['text'], '']
                    if note.get('time') is not None:
                        t = note['time']
                        lines += [f'At {int(t // 60)}:{int(t % 60):02d} (frame {note["frame"]}, segment {json.dumps(note.get("segment"))})', '']
                    if note.get('attachments'):
                        lines += ['Attachments (read-only reference files):']
                        for item in note['attachments']:
                            lines.append(f'- /attachments/{item["name"]} ({item["type"]}, {item["size"]} bytes)')
                        lines += ['Use them as reference. To include one in the video, copy it into the video assets directory and commit it there. Never write into /attachments.', '']
                    for key in ('video', 'film', 'format', 'frame', 'segment', 'beat', 'time', 'image', 'draft'):
                        lines.append(f"{key}: {image if key == 'image' else payload.get(key)}")
                    asking_enabled = not (note.get('no_questions') or note.get('automatic'))
                    if not asking_enabled:
                        lines += ['', '## No more questions', '',
                                  'This note already settles any open choice (either with answers, or by asking '
                                  'you to use your best judgement). Do not ask clarifying questions about it: '
                                  'go ahead and build it.']
                    else:
                        lines += ['', '## Ask first if truly unclear', '',
                                  'Before doing any work, check whether this note leaves open a choice that '
                                  'would substantially change the result, and that nothing already here (this '
                                  'note, the pinned frame, any attachments, or the video itself) settles. If so, '
                                  'stop and ask the director 1 to 3 short questions instead of building: ask '
                                  'before changing anything, and commit nothing. Keep each question short, in '
                                  'plain language (never a file, function or parameter name), and either give it '
                                  '2 to 4 short choices or leave it as free text. End your reply with a line '
                                  'containing only ```questions, then one line of JSON {"questions": '
                                  '[{"text": "...", "choices": ["...", "..."]}]} (omit or empty "choices" for '
                                  'free text), then a line containing only ```, and nothing after it: if you '
                                  'ask, that block is the very end of your reply, with no Summary line. You may '
                                  'put one short line of plain text before the block as a lead-in. If the note '
                                  'is already clear enough, never ask: just build it as usual.']
                    lines += ['', '## Look at your work', '',
                              'Before each distinct step of your work, write one line in your own message '
                              'that starts with "Step: " and says what you are about to do and why, in plain '
                              'words for the director (for example, "Step: make the logo arrive faster in the '
                              'intro"). One line per step, never inside a tool call.',
                              'The director is a creator, not a programmer. In every Step line and in your '
                              'reply, describe what changes on screen in plain language: no file names, function '
                              'or parameter names, code, frame counts or easing names.',
                              'You can see images: open a PNG with the Read tool. When `image` is set it is '
                              'the frame the director was looking at; open it before anything else.',
                              'For anything about how the video looks, iterate visually: `still` the frames the '
                              'note is about and open them, change the code, `still` them again and open them, '
                              'and repeat until the problem is plainly gone when you look, not just in the code. '
                              'A change you can only see side by side has not fixed it. For motion, '
                              '`sheet --frames` around the moment.',
                              'Open your final frames before you reply, and say in the reply what you saw wrong '
                              'and what it looks like now.',
                              '', f"Change files only under {payload.get('directory', video)}.",
                              'Commit only changes to the video. Never commit a reply or notes file: '
                              'end with a short answer for the reviewer as your final message, '
                              'and it is shown to them as your reply.',
                              'Continue the supplied draft, or start from main when draft is null.',
                              'End your reply with Summary: <one line> — unless you are asking clarifying '
                              'questions instead of building, in which case end with the ```questions block '
                              'as described above and do not add a Summary line.'
                              if asking_enabled else 'End your reply with Summary: <one line>.']
                    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                    payload['note_file'] = str(path)
                    note['handle'] = self.backend.submit(payload)
                    note['started'] = time.time()
                    self._save(note)
                    return
                except Exception as e:
                    note.update(state='failed', reply=f'could not submit: {e}')
            else:
                try:
                    status = self.backend.poll(note['handle'])
                    if status.branch and state['draft'] and status.branch != state['draft']:
                        status = AgentStatus('failed', 'Runner returned a different draft branch; '
                                             'continue ' + state['draft'])
                    parsed = parse_questions(status.reply) if status.state == 'replied' else None
                    if parsed:
                        # Strip the raw block from what's shown even when asking is disabled: a backend
                        # that ignores the no-questions instruction must not leak it into the reply.
                        lead_in, questions = parsed
                        if note.get('no_questions') or note.get('automatic'):
                            status = AgentStatus('replied', lead_in or None, status.branch)
                        else:
                            note['questions'] = questions
                            status = AgentStatus('questions', lead_in or None, status.branch)
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
                except Exception as e:
                    note['poll_error'] = str(e)
                    self._save(note)
                    return
            self._save(note)
            if note['state'] not in FINAL:
                return

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

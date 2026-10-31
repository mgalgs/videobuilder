"""Listening notes: a model that can hear audio writes down what a song is
like, for a builder that can't.

    python -m videobuilder listen song.mp3 -o song.listening.md

Gemini (the same $GEMINI_API_KEY and REST call as `say --engine gemini`)
gets the song inline and answers in markdown: genre, mood, instruments and
feel; a timestamped section-by-section timeline; lyrics as heard; the
song's emotional arc; and where a film's scenes could turn. The editor runs
this for every audio attachment on a note (see `Listener`) and stages the
notes beside the file; without the key it does nothing at all. `Listener.warm`
starts listening to an audio file as soon as it is uploaded -- a staged New
video attachment, or an attachment on an existing video -- so the notes are
usually already cached by the time a note needs them; an in-flight note-time
listen for the same audio waits for a warm already underway instead of
asking Gemini again.

The notes are a description, not a measurement: cut on `videobuilder
beats`, not on the timestamps here.
"""
import argparse
import base64
import hashlib
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import speech
from .atomic import write_atomic
from .speech import SpeechUnavailable

LISTEN_MODEL = 'gemini-3.8-flash'
LISTEN_TIMEOUT = 180
# Inline request bodies are capped (about 20 MB on the real API) and base64 adds a third.
INLINE_MAX = 15 * 1048576
INLINE_TYPES = {'.mp3': 'audio/mp3', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.aac': 'audio/aac',
                '.m4a': 'audio/mp4', '.flac': 'audio/flac'}
SUFFIX = '.listening.md'

PROMPT = """\
You are listening to a piece of music so that someone who cannot hear it can \
plan a short film around it. Write your notes in markdown, with these sections:

## Overall
Genre, mood, the instruments and voices you hear, the tempo (an estimate in \
BPM is fine, say it is an estimate) and the feel (straight, swung, half-time, \
driving, floating...).

## Timeline
A section-by-section walk through the track. Start each line with an m:ss \
timestamp and say what changes there: intro, verse, chorus, build, drop, \
break, breakdown, a vocal entering or leaving, a change of key or energy, \
the ending. Include the end time.

## Lyrics
If there are vocals, the words as you hear them, grouped by section with \
timestamps. Mark any line you are not sure of with [unclear] or [?]. If there \
are no vocals, say so.

## Story
The emotional arc of the song from start to finish: where it begins, how it \
moves, where it peaks, how it resolves.

## Where scenes could turn
The moments where a film's scenes could naturally change, with m:ss \
timestamps and a word on why each one works (a hit, a breath, a new section).

Describe only what you actually hear. Whenever you are unsure of something \
(a timestamp, a word, an instrument), say so plainly rather than guessing \
with confidence.
"""


def _key(api_key=None):
    key = api_key or os.environ.get('GEMINI_API_KEY')
    if not key:
        raise SpeechUnavailable(f'listen needs $GEMINI_API_KEY. {speech.GEMINI_HINT}')
    return key


def model():
    return os.environ.get('VIDEOBUILDER_LISTEN_MODEL') or LISTEN_MODEL


def _inline_audio(path, tmp):
    """(mime type, bytes) to send for `path`: the file itself when it is a
    type Gemini takes inline and small enough, else a mono 64 kbps mp3 of it."""
    path = Path(path)
    mime = INLINE_TYPES.get(path.suffix.lower())
    if mime and path.stat().st_size <= INLINE_MAX:
        return mime, path.read_bytes()
    out = Path(tmp) / 'listen.mp3'
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-vn', '-ac', '1', '-b:a', '64k', str(out)],
                       check=True, capture_output=True, timeout=LISTEN_TIMEOUT)
    except FileNotFoundError:
        raise SpeechUnavailable('listen needs ffmpeg to shrink or convert this file') from None
    except subprocess.CalledProcessError as e:
        raise SpeechUnavailable(f"ffmpeg could not read {path.name}: "
                                f"{e.stderr.decode('utf-8', 'replace').strip()[:300]}") from None
    except subprocess.TimeoutExpired:
        raise SpeechUnavailable(f'ffmpeg took too long converting {path.name}') from None
    return 'audio/mp3', out.read_bytes()


def _text(reply, name):
    try:
        parts = reply['candidates'][0]['content']['parts']
        text = ''.join(p.get('text', '') for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        text = ''
    if not text:
        raise SpeechUnavailable(f'Gemini ({name}) returned no notes')
    return text


def listen(path, api_key=None, timeout=LISTEN_TIMEOUT):
    """Markdown listening notes for the audio file at `path`. Raises
    SpeechUnavailable (never carrying the key) when they can't be had."""
    key = _key(api_key)
    name = model()
    url = (os.environ.get('VIDEOBUILDER_GEMINI_URL') or speech.GEMINI_URL).format(model=name)
    try:
        with tempfile.TemporaryDirectory(prefix='vb-listen-') as tmp:
            mime, data = _inline_audio(path, tmp)
        body = {'contents': [{'parts': [
            {'inlineData': {'mimeType': mime, 'data': base64.b64encode(data).decode('ascii')}},
            {'text': PROMPT}]}]}
        reply = speech.gemini_post(url, key, body, lambda code, payload: SpeechUnavailable(
            f'Gemini ({name}): HTTP {code}: {speech.gemini_message(payload)}'), timeout=timeout)
        notes = _text(reply, name)
    except SpeechUnavailable as e:
        raise SpeechUnavailable(str(e).replace(key, '[key]')) from None
    except TimeoutError:   # a read timeout surfaces raw, not as urllib's URLError
        raise SpeechUnavailable(f'no answer within {timeout:g} seconds') from None
    except OSError as e:
        raise SpeechUnavailable(f'{Path(path).name}: {e.strerror or e}'.replace(key, '[key]')) from None
    header = (f'# Listening notes: {Path(path).name}\n\n'
              f'Written by {name}, a model that listened to the audio itself. Its timestamps are '
              'approximate: for exact cut timing, use beat detection on the file.\n\n')
    return header + notes.replace(key, '[key]') + '\n'


def cache_key(data):
    """What a cached note is filed under: the audio's content hash, plus the
    model and prompt, so changing either asks again."""
    h = hashlib.sha256(data).hexdigest()
    return hashlib.sha256(f'{h}\0{model()}\0{PROMPT}'.encode()).hexdigest()


# Keyed by cache_key, shared by every Listener in the process: lets a note-time
# listen for a song a warm() is already fetching wait for that one call instead
# of asking Gemini again (see Listener._notes). Not per-instance, since a
# library's staging warm and a project's own Editor each have their own
# Listener object but can race on the very same audio.
_inflight_lock = threading.Lock()
_inflight = {}


def _claim(key):
    """None if someone else already claimed `key` (the caller should wait,
    not fetch); otherwise an Event this caller must set via `_release` once
    it's done, win or lose."""
    with _inflight_lock:
        if key in _inflight:
            return None
        event = threading.Event()
        _inflight[key] = event
        return event


def _release(key, event):
    with _inflight_lock:
        if _inflight.get(key) is event:
            del _inflight[key]
    event.set()


def _wait(key, timeout):
    with _inflight_lock:
        event = _inflight.get(key)
    if event is not None:
        event.wait(timeout)


class Listener:
    """The editor's listening step: for each audio attachment of a note,
    listening notes staged beside it in the note's attach dir as
    `<name>.listening.md`. Songs are listened to in parallel, each within
    `timeout` seconds; results are cached under `cache_dir` by content, and
    also looked up (never written) under `shared_dir` -- a library's shared
    cache, filled by staged uploads before any video exists (see
    staging.py). Does nothing (returns []) without $GEMINI_API_KEY."""

    def __init__(self, cache_dir, timeout=None, shared_dir=None):
        self.cache_dir = Path(cache_dir)
        self.shared_dir = Path(shared_dir) if shared_dir else None
        self.timeout = timeout

    def warm(self, path, ctype=None):
        """Starts filling the cache for `path` in the background, as soon as
        it's known to be audio -- a no-op without $GEMINI_API_KEY, for a
        file that isn't audio (judged from `ctype` when given, else the
        extension), or when it's already cached or already being fetched
        (by an earlier warm, or a note-time listen already underway).
        Claims the in-flight slot before returning, synchronously, so a
        note-time listen started right after this call reliably finds it
        and waits rather than racing it for ownership. A failure here is
        simply not cached; the note-time listen (__call__) does the work
        itself when it runs."""
        key = os.environ.get('GEMINI_API_KEY')
        if not key:
            return
        path = Path(path)
        is_audio = ctype.startswith('audio/') if ctype else path.suffix.lower() in INLINE_TYPES
        if not is_audio:
            return
        try:
            ck = cache_key(path.read_bytes())
        except OSError:
            return
        if self._cached(ck) is not None:
            return
        event = _claim(ck)
        if event is None:
            return
        timeout = LISTEN_TIMEOUT if self.timeout is None else self.timeout

        def run():
            try:
                self._fetch(path, key, timeout, ck, event)
            except Exception as e:
                print(f'[editor] warming listening notes for {path.name} failed: {e}', file=sys.stderr, flush=True)

        threading.Thread(target=run, daemon=True, name=f'warm {path.name}').start()

    def __call__(self, note, attach_dir):
        """[{name, notes, error}] for the note's audio attachments, `notes`
        the staged file's name (None on failure), `error` why (None on success)."""
        key = os.environ.get('GEMINI_API_KEY')
        songs = [a['name'] for a in note.get('attachments') or [] if str(a.get('type', '')).startswith('audio/')]
        if not key or not attach_dir or not songs:
            return []
        timeout = LISTEN_TIMEOUT if self.timeout is None else self.timeout
        results, lock = {}, threading.Lock()

        def one(name):
            try:
                out = ('ok', self._notes(Path(attach_dir) / name, key, timeout))
            except Exception as e:
                out = ('error', str(e).replace(key, '[key]') or type(e).__name__)
            with lock:
                results[name] = out

        # Daemon threads, not a pool: a hung call must not hold up the note or the editor's exit.
        threads = [threading.Thread(target=one, args=(n,), daemon=True, name=f'listen {n}') for n in songs]
        for t in threads:
            t.start()
        deadline = time.monotonic() + timeout
        for t in threads:
            t.join(max(0, deadline - time.monotonic()))
        with lock:
            done = dict(results)
        out = []
        for name in songs:
            status, value = done.get(name, ('error', f'no answer within {timeout:g} seconds'))
            if status == 'ok':
                staged = name + SUFFIX
                write_atomic(Path(attach_dir) / staged, value)
                out.append({'name': name, 'notes': staged, 'error': None})
            else:
                print(f'[editor] listening to {name} failed: {value}', file=sys.stderr, flush=True)
                out.append({'name': name, 'notes': None, 'error': value})
        return out

    def _cached(self, ck):
        for d in (self.cache_dir, self.shared_dir):
            if d is None:
                continue
            p = d / (ck + '.md')
            if p.is_file():
                try:
                    return p.read_text(encoding='utf-8')
                except OSError:
                    continue
        return None

    def _fetch(self, path, key, timeout, ck, event):
        """Does the actual Gemini call for an already-claimed `ck`, caches
        the result on success, and only then releases the claim -- a waiter
        woken by the release must already find the cache file there, or it
        would just end up fetching it again itself."""
        try:
            notes = listen(path, api_key=key, timeout=timeout)
        except Exception:
            _release(ck, event)
            raise
        try:
            self.cache_dir.mkdir(exist_ok=True)
            write_atomic(self.cache_dir / (ck + '.md'), notes)
        except OSError as e:   # two notes caching the same song at once share write_atomic's .tmp
            print(f'[editor] could not cache listening notes for {path.name}: {e}', file=sys.stderr, flush=True)
        finally:
            _release(ck, event)
        return notes

    def _notes(self, path, key, timeout):
        ck = cache_key(path.read_bytes())
        cached = self._cached(ck)
        if cached is not None:
            return cached
        event = _claim(ck)
        if event is None:
            # A warm(), or another note, is already fetching this same audio:
            # wait for it instead of asking Gemini a second time, then take
            # whatever it left in the cache. On its failure there's nothing to
            # reuse, so fall through and fetch it ourselves.
            _wait(ck, timeout)
            cached = self._cached(ck)
            if cached is not None:
                return cached
            event = _claim(ck)
        if event is not None:
            return self._fetch(path, key, timeout, ck, event)
        return listen(path, api_key=key, timeout=timeout)   # lost the race twice: rare, just do it unclaimed


def main(argv=None):
    p = argparse.ArgumentParser(prog='videobuilder listen',
                                description='listening notes for a song, written by Gemini ($GEMINI_API_KEY)')
    p.add_argument('audio', help='the audio file to listen to')
    p.add_argument('-o', '--out', help='write the notes here (default: print them)')
    a = p.parse_args(argv)
    try:
        notes = listen(a.audio)
    except SpeechUnavailable as e:
        raise SystemExit(f'listen: {e}') from None
    if a.out:
        Path(a.out).write_text(notes, encoding='utf-8')
        print(f'{a.out}: listening notes for {Path(a.audio).name}', file=sys.stderr)
    else:
        sys.stdout.write(notes)

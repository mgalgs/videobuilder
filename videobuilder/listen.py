"""Listening notes: a model that can hear audio writes down what a song is
like, for a builder that can't.

    python -m videobuilder listen song.mp3 -o song.listening.md

Gemini (the same $GEMINI_API_KEY and REST call as `say --engine gemini`)
gets the song inline and answers in markdown: genre, mood, instruments and
feel; a timestamped section-by-section timeline; lyrics as heard; the
song's emotional arc; and where a film's scenes could turn. The editor runs
this for every audio attachment on a note (see `Listener`) and stages the
notes beside the file; without the key it does nothing at all.

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


class Listener:
    """The editor's listening step: for each audio attachment of a note,
    listening notes staged beside it in the note's attach dir as
    `<name>.listening.md`. Songs are listened to in parallel, each within
    `timeout` seconds; results are cached under `cache_dir` by content.
    Does nothing (returns []) without $GEMINI_API_KEY."""

    def __init__(self, cache_dir, timeout=None):
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout

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

    def _notes(self, path, key, timeout):
        cached = self.cache_dir / (cache_key(path.read_bytes()) + '.md')
        if cached.is_file():
            return cached.read_text(encoding='utf-8')
        notes = listen(path, api_key=key, timeout=timeout)
        try:
            self.cache_dir.mkdir(exist_ok=True)
            write_atomic(cached, notes)
        except OSError as e:   # two notes caching the same song at once share write_atomic's .tmp
            print(f'[editor] could not cache listening notes for {path.name}: {e}', file=sys.stderr, flush=True)
        return notes


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

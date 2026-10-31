import base64
import contextlib
import io
import os
import shutil
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest import mock

from tests import fixtures
from tests.fake_gemini import FakeGemini
from tests.test_project import TempProject
from videobuilder import cli, listen, speech
from videobuilder.editor import Editor
from videobuilder.notes import AgentBackend, AgentStatus

KEY = 'test-key-sekrit-123'


def _join_late_listeners():
    """Let a timed-out listen thread finish before its test's directories go."""
    for t in threading.enumerate():
        if t.name.startswith('listen '):
            t.join(10)


def _wav(path, seconds=0.5):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b'\x00\x01' * int(8000 * seconds))


class FakeCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeGemini()
        self.addCleanup(self.fake.close)
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        patcher = mock.patch.dict(os.environ, {'GEMINI_API_KEY': KEY, 'VIDEOBUILDER_GEMINI_URL': self.fake.url})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop('VIDEOBUILDER_LISTEN_MODEL', None)
        sleeper = mock.patch.object(speech.time, 'sleep')
        sleeper.start()
        self.addCleanup(sleeper.stop)


class Listen(FakeCase):
    def test_sends_the_song_inline_with_the_prompt(self):
        song = self.dir / 'song.mp3'
        song.write_bytes(b'ID3' + b'\x00' * 100)
        notes = listen.listen(song)
        (req,) = self.fake.requests
        audio, text = req['contents'][0]['parts']
        self.assertEqual(audio['inlineData']['mimeType'], 'audio/mp3')
        self.assertEqual(base64.b64decode(audio['inlineData']['data']), song.read_bytes())
        self.assertEqual(text['text'], listen.PROMPT)
        self.assertTrue(notes.startswith('# Listening notes: song.mp3\n'))
        self.assertIn('A song (audio/mp3, 103 bytes)', notes)
        self.assertIn(listen.LISTEN_MODEL, notes)

    def test_the_model_is_overridable(self):
        song = self.dir / 'song.mp3'
        song.write_bytes(b'ID3')
        seen = []
        real = speech.gemini_post
        with mock.patch.dict(os.environ, {'VIDEOBUILDER_LISTEN_MODEL': 'gemini-test'}), \
                mock.patch.object(speech, 'gemini_post', lambda url, *a, **k: seen.append(url) or real(url, *a, **k)):
            listen.listen(song)
        self.assertIn('/models/gemini-test:generateContent', seen[0])

    def test_a_big_or_unlisted_file_goes_as_a_mono_mp3(self):
        song = self.dir / 'song.wav'
        _wav(song)
        with mock.patch.object(listen, 'INLINE_MAX', 10):
            listen.listen(song)
        audio = self.fake.requests[0]['contents'][0]['parts'][0]['inlineData']
        self.assertEqual(audio['mimeType'], 'audio/mp3')
        data = base64.b64decode(audio['data'])
        self.assertTrue(data[:3] == b'ID3' or data[:1] == b'\xff', data[:4])

    def test_an_http_error_says_why_without_the_key(self):
        song = self.dir / 'song.mp3'
        song.write_bytes(b'ID3')
        self.fake.queue(400, {'error': {'message': f'API key {KEY} not valid'}})
        with self.assertRaises(speech.SpeechUnavailable) as cm:
            listen.listen(song)
        self.assertIn('HTTP 400', str(cm.exception))
        self.assertIn('not valid', str(cm.exception))
        self.assertNotIn(KEY, str(cm.exception))

    def test_cli_writes_the_notes(self):
        song = self.dir / 'song.mp3'
        song.write_bytes(b'ID3')
        out = self.dir / 'notes.md'
        with contextlib.redirect_stderr(io.StringIO()):
            cli.main(['listen', str(song), '-o', str(out)])
        self.assertIn('## Overall', out.read_text())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(['listen', str(song)])
        self.assertIn('# Listening notes: song.mp3', buf.getvalue())

    def test_cli_without_a_key_names_the_variable(self):
        song = self.dir / 'song.mp3'
        song.write_bytes(b'ID3')
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': ''}), \
                self.assertRaisesRegex(SystemExit, r'listen: listen needs \$GEMINI_API_KEY'):
            cli.main(['listen', str(song)])
        self.assertEqual(self.fake.requests, [])


class ListenerTests(FakeCase):
    def setUp(self):
        super().setUp()
        self.cache = self.dir / 'cache'
        self.attach = self.dir / 'attach'
        self.attach.mkdir()

    def note(self, *songs):
        records = []
        for name, data in songs:
            (self.attach / name).write_bytes(data)
            records.append({'id': name, 'name': name, 'type': 'audio/mpeg', 'size': len(data)})
        return {'attachments': records + [{'id': 'p', 'name': 'pic.png', 'type': 'image/png', 'size': 1}]}

    def test_each_song_gets_notes_and_a_repeat_is_cached(self):
        note = self.note(('a.mp3', b'ID3aaaa'), ('b.mp3', b'ID3bbbbbb'))
        got = listen.Listener(self.cache)(note, str(self.attach))
        self.assertEqual(got, [{'name': 'a.mp3', 'notes': 'a.mp3.listening.md', 'error': None},
                               {'name': 'b.mp3', 'notes': 'b.mp3.listening.md', 'error': None}])
        self.assertIn('7 bytes', (self.attach / 'a.mp3.listening.md').read_text())
        self.assertEqual(len(self.fake.requests), 2)
        other = self.dir / 'other'
        other.mkdir()
        (other / 'renamed.mp3').write_bytes(b'ID3aaaa')
        got = listen.Listener(self.cache)({'attachments': [{'name': 'renamed.mp3', 'type': 'audio/mpeg'}]},
                                          str(other))
        self.assertEqual(got[0]['notes'], 'renamed.mp3.listening.md')
        self.assertEqual(len(self.fake.requests), 2)

    def test_without_a_key_nothing_happens(self):
        note = self.note(('a.mp3', b'ID3'))
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            self.assertEqual(listen.Listener(self.cache)(note, str(self.attach)), [])
        self.assertEqual(self.fake.requests, [])
        self.assertEqual(sorted(p.name for p in self.attach.iterdir()), ['a.mp3'])

    def test_a_hung_call_times_out_and_is_not_staged(self):
        note = self.note(('a.mp3', b'ID3'))
        self.fake.delay = 1
        with contextlib.redirect_stderr(io.StringIO()):
            got = listen.Listener(self.cache, timeout=0.3)(note, str(self.attach))
        self.assertEqual(got[0]['notes'], None)
        self.assertIn('no answer within 0.3 seconds', got[0]['error'])
        self.assertFalse((self.attach / 'a.mp3.listening.md').exists())
        with contextlib.redirect_stderr(io.StringIO()):
            _join_late_listeners()

    def test_an_error_is_reported_without_the_key(self):
        note = self.note(('a.mp3', b'ID3'))
        self.fake.queue(403, {'error': {'message': f'key {KEY} is blocked'}})
        with contextlib.redirect_stderr(io.StringIO()) as err:
            got = listen.Listener(self.cache)(note, str(self.attach))
        self.assertIn('blocked', got[0]['error'])
        self.assertNotIn(KEY, got[0]['error'])
        self.assertNotIn(KEY, err.getvalue())
        self.assertFalse(self.cache.exists() and any(self.cache.iterdir()))



class Recorder(AgentBackend):
    """Takes each submitted note's prompt and staged files as the builder would
    find them, then answers at once so the next note goes out."""
    name = 'recorder'

    def __init__(self):
        self.seen = []

    def submit(self, payload):
        attach = Path(payload['attach_dir']) if payload.get('attach_dir') else None
        files = {p.name: p.read_text() if p.suffix == '.md' else p.read_bytes()
                 for p in attach.iterdir() if p.is_file()} if attach else {}
        self.seen.append((Path(payload['note_file']).read_text(), files))
        return 'rec:' + payload['id']

    def poll(self, handle):
        return AgentStatus('failed', 'done')


MP3_A, MP3_B = b'ID3' + b'a' * 40, b'ID3' + b'b' * 50


class NoteListening(TempProject):
    """A note's attached songs, listened to by the editor against tests/fake_gemini.py."""

    def setUp(self):
        super().setUp()
        self.fake = FakeGemini()
        self.addCleanup(self.fake.close)
        patcher = mock.patch.dict(os.environ, {'GEMINI_API_KEY': KEY, 'VIDEOBUILDER_GEMINI_URL': self.fake.url})
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch.object(speech.time, 'sleep')
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.backend = Recorder()
        self.editor = Editor(self.root, backend=self.backend, unsandboxed_previews=True, auto_land=False)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        self.addCleanup(fixtures.settle, self.editor)

    def note(self, *songs):
        ids = [self.editor.attachments.upload('promo/film', name, 'audio/mpeg', data)['id'] for name, data in songs]
        ids.append(self.editor.attachments.upload('promo/film', 'ref.png', 'image/png',
                                                  b'\x89PNG\r\n\x1a\n0123')['id'])
        self.editor.add_note(dict(video='promo/film', frame=0, text='Cut it to the songs', attachments=ids),
                             'reviewer')
        fixtures.settle(self.editor)
        self.editor.notes.list()
        fixtures.settle(self.editor)
        return self.backend.seen[-1]

    def test_two_songs_get_notes_and_a_prompt_section(self):
        prompt, files = self.note(('one.mp3', MP3_A), ('two.mp3', MP3_B))
        self.assertEqual(sorted(files), ['one.mp3', 'one.mp3.listening.md', 'pinned-frame.png', 'ref.png', 'two.mp3',
                                         'two.mp3.listening.md'])
        self.assertIn('A song (audio/mp3, 43 bytes)', files['one.mp3.listening.md'])
        self.assertIn('A song (audio/mp3, 53 bytes)', files['two.mp3.listening.md'])
        self.assertIn('## Listening notes', prompt)
        self.assertIn('A model that actually listened to the audio', prompt)
        self.assertIn('- /attachments/one.mp3: read /attachments/one.mp3.listening.md', prompt)
        self.assertIn('- /attachments/two.mp3: read /attachments/two.mp3.listening.md', prompt)
        self.assertEqual(len(self.fake.requests), 2)
        self.assertNotIn(KEY, prompt + ''.join(v for v in files.values() if isinstance(v, str)))

    def test_the_same_song_on_a_later_note_is_not_listened_to_again(self):
        self.note(('one.mp3', MP3_A))
        prompt, files = self.note(('again.mp3', MP3_A))
        self.assertEqual(len(self.fake.requests), 1)
        self.assertIn('- /attachments/again.mp3: read /attachments/again.mp3.listening.md', prompt)
        self.assertIn('43 bytes', files['again.mp3.listening.md'])

    def test_an_error_still_runs_the_note_and_says_listening_failed(self):
        self.fake.queue(400, {'error': {'message': f'bad request for key {KEY}'}})
        with contextlib.redirect_stderr(io.StringIO()) as err:
            prompt, files = self.note(('one.mp3', MP3_A))
        self.assertIn('- /attachments/one.mp3: listening failed (', prompt)
        self.assertIn('HTTP 400', prompt)
        self.assertNotIn('one.mp3.listening.md', files)
        self.assertNotIn('A model that actually listened', prompt)
        self.assertNotIn(KEY, prompt)
        self.assertNotIn(KEY, err.getvalue())

    def test_a_hang_past_the_timeout_still_runs_the_note(self):
        self.fake.delay = 1
        self.editor.notes.listen.timeout = 0.3
        with contextlib.redirect_stderr(io.StringIO()):
            prompt, files = self.note(('one.mp3', MP3_A))
            _join_late_listeners()
        self.assertIn('- /attachments/one.mp3: listening failed (no answer within 0.3 seconds)', prompt)
        self.assertNotIn('one.mp3.listening.md', files)

    def test_without_a_key_prompt_and_staging_are_as_before(self):
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            prompt, files = self.note(('one.mp3', MP3_A))
        self.editor.notes.listen = None
        bare_prompt, bare_files = self.note(('one.mp3', MP3_A))
        self.assertEqual(self.fake.requests, [])
        self.assertEqual(sorted(files), ['one.mp3', 'pinned-frame.png', 'ref.png'])
        self.assertEqual(files, bare_files)
        self.assertEqual(prompt, bare_prompt)
        self.assertNotIn('Listening', prompt)

if __name__ == '__main__':
    unittest.main()

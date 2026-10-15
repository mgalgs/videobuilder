"""Source videos: upload, list, preview, delete; limits enforced as bytes
stream in; staging into the editor's own checkouts and the builder's."""
import io
import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from videobuilder.editor import Editor
from videobuilder.sources import CAPTION_MAX_BYTES, PREVIEW_MAX_SIDE, Sources, TooLarge
from tests import fixtures
from tests.test_project import TempProject, git

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')


def _mp4(path, seconds=1, size='64x64', audio=False):
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=blue:s={size}:d={seconds}:r=10']
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}', '-shortest']
    cmd += ['-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(cmd, check=True, capture_output=True)


def _audio_only_mp4(path, seconds=1):
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
                    '-c:a', 'aac', str(path)], check=True, capture_output=True)


class _Rfile:
    """Wraps a BytesIO, recording each `.read(n)` call's size: lets a test
    assert an upload is streamed in bounded chunks, never one big read."""

    def __init__(self, data):
        self.buf = io.BytesIO(data)
        self.calls = []

    def read(self, n):
        self.calls.append(n)
        return self.buf.read(n)


@unittest.skipUnless(FFMPEG, 'needs ffmpeg/ffprobe')
class DirectUpload(fixtures.API):
    """Direct, Python-level tests against Sources.stream_upload."""

    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.clip = Path(self.scratch.name) / 'clip.mp4'
        _mp4(self.clip, audio=True)

    def _upload(self, filename='clip.mp4', name=None, data=None, content_type='video/mp4', video='promo/film'):
        data = data if data is not None else self.clip.read_bytes()
        rfile = _Rfile(data)
        record = self.editor.sources.stream_upload(video, filename, name, content_type, rfile, len(data))
        return record, rfile

    def test_upload_records_duration_resolution_and_audio(self):
        record, _ = self._upload()
        self.assertEqual(record['name'], 'clip')
        self.assertEqual(record['ext'], 'mp4')
        self.assertEqual((record['width'], record['height']), (64, 64))
        self.assertTrue(record['has_audio'])
        self.assertAlmostEqual(record['duration'], 1.0, delta=0.2)
        self.assertIsNone(record['caption'])

    def test_upload_streams_in_bounded_chunks_not_one_big_read(self):
        with mock.patch('videobuilder.sources.STREAM_CHUNK', 256):
            record, rfile = self._upload()
        self.assertGreater(len(rfile.calls), 1)
        self.assertTrue(all(n <= 256 for n in rfile.calls))

    def test_explicit_name_overrides_the_filename_stem(self):
        record, _ = self._upload(name='Interview Clip!')
        self.assertEqual(record['name'], 'interview-clip')

    def test_odd_unicode_and_traversal_in_filename_are_sanitized(self):
        record, _ = self._upload(filename='../../etc/pâssÃ©é/clîp éé.mp4')
        self.assertRegex(record['name'], r'^[a-z0-9-]+$')
        video_dir = self.editor.sources._video_dir('promo/film')
        for path in video_dir.glob('**/*'):
            self.assertTrue(path.resolve().is_relative_to(video_dir.resolve()), path)

    def test_name_clash_is_refused_with_nothing_left_on_disk(self):
        self._upload(name='interview')
        before = sorted(p.name for p in self.editor.sources._video_dir('promo/film').iterdir())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self._upload(name='interview')
        after = sorted(p.name for p in self.editor.sources._video_dir('promo/film').iterdir())
        self.assertEqual(before, after)

    def test_wrong_extension_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'mp4, .mov or .webm'):
            self._upload(filename='clip.avi')

    def test_content_type_mismatch_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Content-Type'):
            self._upload(content_type='video/quicktime')

    def test_bad_magic_bytes_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'magic bytes'):
            self._upload(data=b'not actually a video' + b'0' * 100)

    def test_file_with_no_video_stream_is_refused(self):
        audio_only = Path(self.scratch.name) / 'audio.mp4'
        _audio_only_mp4(audio_only)
        with self.assertRaisesRegex(ValueError, 'no video stream'):
            self._upload(filename='audio.mp4', data=audio_only.read_bytes())

    def _nothing_left(self):
        video_dir = self.editor.sources._video_dir('promo/film')
        return set(video_dir.rglob('*')) if video_dir.is_dir() else set()

    def test_over_per_file_limit_is_too_large_with_nothing_left(self):
        self.editor.sources.max_file = 10
        before = self._nothing_left()
        with self.assertRaises(TooLarge):
            self._upload()
        self.assertEqual(self._nothing_left(), before)

    def test_over_total_limit_is_too_large_with_nothing_left(self):
        self._upload(name='first')
        self.editor.sources.max_total = self.editor.sources._total_bytes('promo/film')
        before = self._nothing_left()
        with self.assertRaises(TooLarge):
            self._upload(name='second')
        self.assertEqual(self._nothing_left(), before)

    def test_missing_content_length_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Content-Length'):
            self.editor.sources.stream_upload('promo/film', 'clip.mp4', None, 'video/mp4', _Rfile(b'x'), -1)

    def test_unknown_video_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self._upload(video='nope/film')

    def test_caption_upload_vtt_and_srt(self):
        self._upload(name='interview')
        vtt = b'WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n'
        record = self.editor.sources.add_caption('promo/film', 'interview', 'cc.vtt', vtt)
        self.assertEqual(record['caption'], 'interview.vtt')
        path = self.editor.sources._dir('promo/film', 'interview') / 'interview.vtt'
        self.assertEqual(path.read_bytes(), vtt)
        srt = b'1\n00:00:00,000 --> 00:00:01,000\nHi\n'
        record = self.editor.sources.add_caption('promo/film', 'interview', 'cc.srt', srt)
        self.assertEqual(record['caption'], 'interview.srt')
        self.assertFalse(path.exists())  # the stale .vtt was replaced

    def test_caption_rejects_bad_extension_non_utf8_and_oversize(self):
        self._upload(name='interview')
        with self.assertRaisesRegex(ValueError, 'vtt or .srt'):
            self.editor.sources.add_caption('promo/film', 'interview', 'cc.txt', b'hi')
        with self.assertRaisesRegex(ValueError, 'UTF-8'):
            self.editor.sources.add_caption('promo/film', 'interview', 'cc.vtt', b'\xff\xfe\x00')
        with self.assertRaisesRegex(ValueError, 'too large'):
            self.editor.sources.add_caption('promo/film', 'interview', 'cc.vtt', b'0' * (CAPTION_MAX_BYTES + 1))

    def test_delete_removes_files_and_unknown_raises_keyerror(self):
        self._upload(name='interview')
        d = self.editor.sources._dir('promo/film', 'interview')
        self.assertTrue(d.is_dir())
        self.editor.sources.delete('promo/film', 'interview')
        self.assertFalse(d.exists())
        with self.assertRaises(KeyError):
            self.editor.sources.delete('promo/film', 'interview')

    @staticmethod
    def _slow_ffmpeg(delay):
        """A subprocess.run stand-in that sleeps before any ffmpeg call, so a
        test can reliably land an operation while the background preview
        build (see Sources._build_preview) is still encoding."""
        real_run = subprocess.run

        def slow_run(cmd, **kw):
            if cmd and cmd[0] == 'ffmpeg':
                time.sleep(delay)
            return real_run(cmd, **kw)
        return slow_run

    def test_add_caption_mid_build_does_not_clobber_preview_ready(self):
        # The caption's own meta read used to happen before the lock; saving that
        # stale copy once the lock was free could overwrite preview_ready=True
        # (set by the build, which finished while this held the lock) with a
        # stale False, leaving the source permanently stuck as "Preparing...".
        with mock.patch('videobuilder.sources.subprocess.run', side_effect=self._slow_ffmpeg(0.5)):
            self._upload(name='interview')
            time.sleep(0.1)  # the background build is now inside the slowed ffmpeg call
            self.editor.sources.add_caption('promo/film', 'interview', 'cc.vtt', b'WEBVTT\n')
            self._wait_for_preview('interview')
        final = self.editor.sources.get('promo/film', 'interview')
        self.assertTrue(final['preview_ready'])
        self.assertEqual(final['caption'], 'interview.vtt')

    def test_delete_does_not_wait_for_the_whole_encode(self):
        # delete() used to take the same lock _build_preview held for the entire
        # ffmpeg encode, so deleting a source mid-build waited for the encode
        # (minutes, for a large source) instead of returning right away.
        with mock.patch('videobuilder.sources.subprocess.run', side_effect=self._slow_ffmpeg(1)):
            self._upload(name='interview')
            time.sleep(0.2)  # the background build is now inside the slowed ffmpeg call
            started = time.monotonic()
            self.editor.sources.delete('promo/film', 'interview')
            self.assertLess(time.monotonic() - started, 0.5)

    def test_name_traversal_is_refused_everywhere_not_just_in_the_filename(self):
        # 'name' here models what a URL path segment like /api/sources/../delete
        # hands the store directly: `[^/]+` in the route regex lets '..' and '.'
        # through unchanged (see video_api.py / handler_library.py), so delete,
        # get and add_caption must each refuse it themselves rather than resolving
        # it against the sources root or the video's own directory.
        self._upload(name='interview')
        root_before = sorted(p.name for p in self.editor.sources.root.iterdir())
        for bad in ('..', '.', 'INTERVIEW', 'inter view', 'a/b', ''):
            with self.subTest(bad=bad):
                with self.assertRaises(KeyError):
                    self.editor.sources.get('promo/film', bad)
                with self.assertRaises(KeyError):
                    self.editor.sources.delete('promo/film', bad)
                with self.assertRaises(KeyError):
                    self.editor.sources.add_caption('promo/film', bad, 'cc.vtt', b'WEBVTT\n')
        self.assertEqual(sorted(p.name for p in self.editor.sources.root.iterdir()), root_before)

    def test_list_is_sorted_and_public_shape(self):
        self._upload(name='b-clip')
        self._upload(name='a-clip')
        names = [s['name'] for s in self.editor.sources.list('promo/film')]
        self.assertEqual(names, ['a-clip', 'b-clip'])
        for s in self.editor.sources.list('promo/film'):
            self.assertEqual(set(s), {'name', 'ext', 'size', 'duration', 'width', 'height',
                                      'has_audio', 'caption', 'created', 'preview_ready'})

    def _wait_for_preview(self, name, timeout=10):
        deadline = time.monotonic() + timeout
        while not self.editor.sources.get('promo/film', name)['preview_ready']:
            if time.monotonic() > deadline:
                self.fail(f'preview for {name!r} never became ready')
            time.sleep(0.05)
        return self.editor.sources._preview_path('promo/film', name)

    def test_preview_copy_is_made_off_the_request_thread(self):
        record, _ = self._upload()
        self.assertFalse(record['preview_ready'])
        preview = self.editor.sources._preview_path('promo/film', record['name'])
        # stream_upload already returned: proven by reaching this assertion before the
        # background ffmpeg encode (which needs at least a process fork+exec) can have run.
        self.assertFalse(preview.exists())
        self._wait_for_preview(record['name'])
        self.assertTrue(self.editor.sources.get('promo/film', record['name'])['preview_ready'])

    def test_preview_copy_keeps_source_fps_and_caps_the_short_side(self):
        big = Path(self.scratch.name) / 'big.mp4'
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=800x450:d=1:r=24',
                       '-pix_fmt', 'yuv420p', str(big)], check=True, capture_output=True)
        record, _ = self._upload(filename='big.mp4', data=big.read_bytes())
        preview = self._wait_for_preview(record['name'])
        probed = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'json', str(preview)],
            capture_output=True, text=True, check=True)
        stream = json.loads(probed.stdout)['streams'][0]
        self.assertEqual(min(stream['width'], stream['height']), PREVIEW_MAX_SIDE)
        self.assertEqual(stream['r_frame_rate'], '24/1')

    def test_preview_copy_is_deleted_with_its_source(self):
        record, _ = self._upload()
        preview = self._wait_for_preview(record['name'])
        self.editor.sources.delete('promo/film', record['name'])
        self.assertFalse(preview.exists())

    def test_restart_rebuilds_a_pending_preview_and_sweeps_stale_scratch(self):
        # An editor restart mid-encode (every release restarts it) used to leave
        # preview_ready stuck False forever, since nothing else polled for it.
        self._upload(name='interview')
        self._wait_for_preview('interview')
        meta = self.editor.sources.get('promo/film', 'interview')
        meta['preview_ready'] = False
        self.editor.sources._save('promo/film', 'interview', meta)
        stale = self.editor.sources._tmp_dir / '.tmp-leftover'
        stale.write_bytes(b'leftover scratch from an interrupted build')

        fresh = Sources(self.editor, self.editor.sources.max_file, self.editor.sources.max_total)
        self.assertFalse(stale.exists())
        deadline = time.monotonic() + 10
        while not fresh.get('promo/film', 'interview')['preview_ready']:
            if time.monotonic() > deadline:
                self.fail('preview was never rebuilt after a fresh Sources was constructed')
            time.sleep(0.05)

    def test_builds_run_one_at_a_time_not_concurrently(self):
        in_flight = []
        max_seen = [0]
        lock = threading.Lock()
        real_run = subprocess.run

        def tracking_run(cmd, **kw):
            if cmd and cmd[0] == 'ffmpeg':
                with lock:
                    in_flight.append(1)
                    max_seen[0] = max(max_seen[0], len(in_flight))
                time.sleep(0.3)
                with lock:
                    in_flight.pop()
            return real_run(cmd, **kw)

        with mock.patch('videobuilder.sources.subprocess.run', side_effect=tracking_run):
            self._upload(name='first')
            self._upload(name='second')
            self._wait_for_preview('first')
            self._wait_for_preview('second')
        self.assertEqual(max_seen[0], 1)


@unittest.skipUnless(FFMPEG, 'needs ffmpeg/ffprobe')
class CheckoutStaging(fixtures.API):
    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.clip = Path(self.scratch.name) / 'clip.mp4'
        _mp4(self.clip)
        with open(self.clip, 'rb') as fh:
            data = fh.read()
        self.editor.sources.stream_upload('promo/film', 'interview.mp4', None, 'video/mp4', _Rfile(data), len(data))

    def test_sync_hardlinks_into_the_main_checkout_and_is_git_ignored(self):
        self.editor.sources.sync('promo/film')
        linked = self.root / 'promo' / 'sources' / 'interview.mp4'
        self.assertTrue(linked.is_file())
        self.assertEqual(linked.stat().st_ino, (self.editor.sources._dir('promo/film', 'interview')
                                                / 'interview.mp4').stat().st_ino)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        exclude = (self.root / '.git' / 'info' / 'exclude').read_text()
        self.assertIn('/promo/sources/', exclude.splitlines())

    def test_exclude_entry_is_anchored_to_the_video_dir_not_any_sources_dir(self):
        # A bare `sources/` would also match an unrelated `sources/` directory
        # elsewhere in the creator's repo; the entry must be anchored to this
        # video's own directory.
        self.editor.sources.sync('promo/film')
        exclude = (self.root / '.git' / 'info' / 'exclude').read_text().splitlines()
        self.assertNotIn('sources/', exclude)
        other = self.root / 'unrelated' / 'sources'
        other.mkdir(parents=True)
        (other / 'keep.txt').write_text('not excluded')
        self.assertEqual(git(self.root, 'status', '--porcelain', '--ignored=matching', '--', 'unrelated').strip(),
                         '?? unrelated/')

    def test_sync_removes_a_stale_link_after_delete(self):
        self.editor.sources.sync('promo/film')
        linked = self.root / 'promo' / 'sources' / 'interview.mp4'
        self.assertTrue(linked.exists())
        self.editor.sources.delete('promo/film', 'interview')
        self.assertFalse(linked.exists())

    def test_sync_with_no_sources_leaves_an_unrelated_sources_dir_alone(self):
        # A `sources/` folder the creator already had, unrelated to this feature, must
        # survive a sync() for a video that has none of its own -- sync() used to
        # shutil.rmtree() the whole directory in that case.
        self.editor.sources.delete('promo/film', 'interview')
        unrelated = self.root / 'promo' / 'sources'
        unrelated.mkdir()
        (unrelated / 'notes.txt').write_text('keep me')
        self.editor.sources.sync('promo/film')
        self.assertEqual((unrelated / 'notes.txt').read_text(), 'keep me')

    def test_sync_does_not_unlink_a_subdirectory_sharing_the_sources_dir(self):
        # A subdirectory sitting alongside the hardlinks (unrelated to any source
        # name) used to raise IsADirectoryError on sync() -- real content, not ours,
        # must be left in place instead.
        self.editor.sources.sync('promo/film')
        nested = self.root / 'promo' / 'sources' / 'notes'
        nested.mkdir()
        (nested / 'a.txt').write_text('keep me too')
        self.editor.sources.sync('promo/film')  # must not raise
        self.assertTrue((nested / 'a.txt').is_file())

    def test_sync_into_a_draft_worktree(self):
        work = Path(self.scratch.name) / 'worktree'
        git(self.root, 'worktree', 'add', '--detach', str(work), 'main')
        # No explicit `worktree remove`: self.root (and so .git/worktrees/...) is gone
        # once TempProject.tearDown() removes the whole temp project anyway.
        self.editor.sources.sync('promo/film', root=work)
        self.assertTrue((work / 'promo' / 'sources' / 'interview.mp4').is_file())

    def _wait_for_preview(self, name, timeout=10):
        deadline = time.monotonic() + timeout
        while not self.editor.sources.get('promo/film', name)['preview_ready']:
            if time.monotonic() > deadline:
                self.fail(f'preview for {name!r} never became ready')
            time.sleep(0.05)

    def test_stage_for_builder_copies_ready_previews_not_hardlinks(self):
        self._wait_for_preview('interview')
        dest = Path(self.scratch.name) / 'attach'
        dest.mkdir()
        added = self.editor.sources.stage_for_builder('promo/film', dest, budget=1 << 30)
        self.assertEqual(added, {'interview'})
        staged = dest / 'sources' / 'interview.mp4'
        self.assertTrue(staged.is_file())
        self.assertEqual(staged.stat().st_nlink, 1)  # a copy, not a hardlink

    def test_stage_for_builder_skips_a_source_not_yet_ready(self):
        dest = Path(self.scratch.name) / 'attach'
        dest.mkdir()
        added = self.editor.sources.stage_for_builder('promo/film', dest, budget=1 << 30)
        self.assertEqual(added, set())
        self.assertFalse((dest / 'sources').exists())

    def test_stage_for_builder_stops_once_the_next_one_would_exceed_budget(self):
        self._wait_for_preview('interview')
        dest = Path(self.scratch.name) / 'attach'
        dest.mkdir()
        added = self.editor.sources.stage_for_builder('promo/film', dest, budget=1)
        self.assertEqual(added, set())
        self.assertFalse((dest / 'sources' / 'interview.mp4').exists())

    def test_stage_for_builder_with_no_sources_adds_nothing(self):
        self.editor.sources.delete('promo/film', 'interview')
        dest = Path(self.scratch.name) / 'attach'
        dest.mkdir()
        added = self.editor.sources.stage_for_builder('promo/film', dest, budget=1 << 30)
        self.assertEqual(added, set())
        self.assertFalse((dest / 'sources').exists())

    def test_draft_preview_renders_a_source_with_vb_clip(self):
        # The path a note-driven builder is told to use (prompt.py): built from the film
        # file's own directory, not a plain relative path -- the working directory itself
        # differs between a preview, a render and the builder's sandbox, but `__file__`
        # resolves the same way everywhere, into the directory sources.sync() hardlinks
        # sources into.
        self.editor.sources.sync('promo/film')
        self.film.write_text(
            "import os\n"
            "import videobuilder as vb\n"
            "T = vb.Timeline(vb.Grid(fps=10, bpm=120), [vb.Segment('tiny', 0, 1)], end=1)\n"
            "_clip = vb.Clip(os.path.join(os.path.dirname(__file__), 'sources', 'interview.mp4'))\n"
            "def draw(n, cv):\n"
            "    cv.rect(0, 0, cv.width, cv.height, '#101418')\n"
            "    cv.image(_clip.frame(0), 0, 0, cv.width, cv.height)\n"
            "FILM = vb.Film(draw=draw, timeline=T, formats=('1x1',))\n")
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'use a source clip')
        png = self.editor.session('promo/film').request('frame', frame=0, format='1x1', scale=1.0)
        self.assertTrue(png.startswith(b'\x89PNG'))


@unittest.skipUnless(FFMPEG, 'needs ffmpeg/ffprobe')
class HTTPRoundTrip(fixtures.API):
    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.clip = Path(self.scratch.name) / 'clip.mp4'
        _mp4(self.clip)

    def _post_raw(self, path, data, ctype='video/mp4'):
        req = urllib.request.Request(self.base + path, data=data, method='POST', headers={'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            with exc:
                try:
                    return exc.code, json.loads(exc.read())
                except ValueError:
                    return exc.code, None

    def test_upload_list_preview_delete_round_trip(self):
        code, record = self._post_raw('/api/sources?video=promo/film&filename=clip.mp4', self.clip.read_bytes())
        self.assertEqual(code, 201, record)
        self.assertEqual(record['name'], 'clip')
        listed = self.get('/api/sources?video=promo/film')
        self.assertEqual([s['name'] for s in listed['sources']], ['clip'])
        with urllib.request.urlopen(self.base + '/api/sources/clip?video=promo/film') as r:
            self.assertEqual(r.headers.get('Accept-Ranges'), 'bytes')
            self.assertEqual(r.read(), self.clip.read_bytes())
        code, body = self.post('/api/sources/clip/delete', {'video': 'promo/film'})
        self.assertEqual((code, body), (200, {'deleted': 'clip'}))
        self.assertEqual(self.get('/api/sources?video=promo/film')['sources'], [])

    def test_preview_serves_a_byte_range_without_reading_the_whole_file(self):
        self._post_raw('/api/sources?video=promo/film&filename=clip.mp4', self.clip.read_bytes())
        data = self.clip.read_bytes()
        with mock.patch('pathlib.Path.read_bytes', side_effect=AssertionError('must not read the whole file')):
            req = urllib.request.Request(self.base + '/api/sources/clip?video=promo/film',
                                         headers={'Range': f'bytes=1-{len(data) - 2}'})
            with urllib.request.urlopen(req, timeout=20) as r:
                self.assertEqual(r.status, 206)
                self.assertEqual(r.read(), data[1:len(data) - 1])

    def test_delete_still_refuses_a_traversal_name_through_the_http_route(self):
        code, _ = self._post_raw('/api/sources?video=promo/film&filename=clip.mp4', self.clip.read_bytes())
        self.assertEqual(code, 201)
        code, body = self.post('/api/sources/../delete', {'video': 'promo/film'})
        self.assertEqual(code, 404, body)
        self.assertEqual([s['name'] for s in self.get('/api/sources?video=promo/film')['sources']], ['clip'])

    def test_unknown_source_preview_is_404(self):
        req = urllib.request.Request(self.base + '/api/sources/nope?video=promo/film')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 404)

    def test_delete_unknown_source_is_404(self):
        code, body = self.post('/api/sources/nope/delete', {'video': 'promo/film'})
        self.assertEqual(code, 404)

    def test_over_file_limit_is_413_with_nothing_left(self):
        self.editor.sources.max_file = len(self.clip.read_bytes()) - 1
        code, body = self._post_raw('/api/sources?video=promo/film&filename=clip.mp4', self.clip.read_bytes())
        self.assertEqual(code, 413, body)
        self.assertEqual(self.get('/api/sources?video=promo/film')['sources'], [])

    def test_caption_upload_route(self):
        self._post_raw('/api/sources?video=promo/film&filename=clip.mp4', self.clip.read_bytes())
        vtt = b'WEBVTT\n\n00:00.000 --> 00:01.000\nHi\n'
        code, record = self._post_raw('/api/sources/clip/caption?video=promo/film&filename=cc.vtt', vtt,
                                      ctype='text/vtt')
        self.assertEqual(code, 201, record)
        self.assertEqual(record['caption'], 'clip.vtt')

    def test_unsupported_extension_is_400(self):
        code, body = self._post_raw('/api/sources?video=promo/film&filename=clip.avi', b'0' * 100)
        self.assertEqual(code, 400, body)


class ConfigKeys(TempProject):
    def _editor(self, state_dir, **kw):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_defaults(self):
        editor = self._editor('state-defaults')
        self.assertEqual(editor.sources.max_file, 2048 * 1048576)
        self.assertEqual(editor.sources.max_total, 8192 * 1048576)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\nsource_max_mb = 5\nsource_max_total_mb = 11\n')
        editor = self._editor('state-configured')
        self.assertEqual(editor.sources.max_file, 5 * 1048576)
        self.assertEqual(editor.sources.max_total, 11 * 1048576)

    def test_explicit_kwargs_override_config_for_library_mode(self):
        editor = self._editor('state-kwargs', source_max_mb=3, source_max_total_mb=7)
        self.assertEqual(editor.sources.max_file, 3 * 1048576)
        self.assertEqual(editor.sources.max_total, 7 * 1048576)


class CLIFlags(unittest.TestCase):
    def test_refused_outside_library_mode(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--source-max-mb', '5'])
        self.assertIn('--source-max-mb', str(e.exception))
        self.assertIn('--library mode', str(e.exception))
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--source-max-total-mb', '5'])
        self.assertIn('--source-max-total-mb', str(e.exception))

    def test_must_be_positive(self):
        from videobuilder.cli import main
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--source-max-mb', '0'])
            self.assertIn('source_max_mb', str(e.exception))

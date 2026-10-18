"""Notes on a film made of clips: the `clip` field, and what the builder is told."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from videobuilder import assembly, film_brief
from videobuilder.clip_cache import GitTree
from videobuilder.notes import AgentStatus, NoteStore

from tests import fixtures
from tests.test_films import QUIET, make_media, three_clips, write_film
from tests.test_notes import FakeAgent
from tests.test_project import TempProject, git

HAS_FFMPEG = shutil.which('ffmpeg') is not None


def film_repo(root):
    """A repo whose `promo/` is a film of clips (a, boat, c) with a bible."""
    promo = Path(root) / 'promo'
    write_film(promo, {**three_clips(), 'acts': [{'title': 'The river', 'clips': ['a', 'boat']}]})
    (promo / 'film.py').write_text('"""The title film."""\n')
    film = promo / 'clips' / 'c' / 'film.py'
    film.write_text('"""The credits roll over the river at dusk.\n\nMore detail."""\n' + film.read_text())
    (promo / 'bible' / 'characters').mkdir(parents=True)
    (promo / 'bible' / 'bible.md').write_text('# Look\n')
    (promo / 'bible' / 'characters' / 'mara.md').write_text('# Mara\n')
    (promo / 'bible' / 'characters' / 'mara.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'a film')
    return git(root, 'rev-parse', 'HEAD').strip()


# What the editor's Drafts.context gives a video at promo/film.py, as far as the prompt uses it.
DIRECTORY = lambda video: {'directory': 'promo'}  # noqa: E731

CLIP_NOTE_GOLDEN = '''\
# Review request

Make the credits warmer

video: promo/film
film: None
format: 1x1
frame: None
segment: None
beat: None
time: None
image: None
draft: None

## This note is about one clip

This video is a film made of clips: `promo/timeline.json` lists them in order, each built and \
rendered on its own, then cut together (read skill/make-a-video/reference/films.md). This note is \
about clip 3 of 3, `c`, whose film is `promo/clips/c/film.py`.
What it is for: The credits roll over the river at dusk.
Before it: clip 2, `boat` (footage from promo/sources/boat.mp4); it cuts into this clip with a wipe \
to the left over 6 frames.
It is the last clip.
Keep the edges consistent: unless the note asks otherwise, this clip begins where the one before it \
leaves off and ends where the one after it picks up, with the same characters, colours, light and \
framing either side of each cut.
A clip imports shared code as `from shared import ...`, with the video's directory on its import \
path: add that directory to PYTHONPATH beside the videobuilder this video renders with (the pinned \
source, if one is named below), not in place of it, `PYTHONPATH=promo:$PYTHONPATH python -m \
videobuilder still promo/clips/c/film.py 0`.

## The bible

`promo/bible/` describes the whole film: its look, world, tone and outline (`bible.md`) and its \
characters (`characters/`). Read it first, and keep characters and the look consistent with it. \
Open its pictures with the Read tool.

- promo/bible/bible.md
- promo/bible/characters/mara.md
- promo/bible/characters/mara.png

A clip note never changes the bible: when this clip has to depart from it, say so in your reply.
'''

CLIP_NOTE_SCOPE_GOLDEN = '''\
Change files only under promo/clips/c.
Only when the note asks for something every clip uses (a shared palette, font or character drawing) \
may you change promo/shared/ too: that re-renders every clip, so look at another clip afterwards and \
say in your reply that you changed it. Never change promo/timeline.json or another clip's directory \
in a clip note; if the note needs that, build what you can in this clip and say what else it needs.
'''


class FilmPrompt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name, 'repo')
        self.repo.mkdir()
        self.sha = film_repo(self.repo)
        self.cache = assembly.ClipCache(Path(self.tmp.name, 'clips'))
        self.store = NoteStore(Path(self.tmp.name, 'notes'), FakeAgent(), context=DIRECTORY)
        self.store.film = lambda video, note, state: film_brief.brief(
            self.repo, self.sha, 'promo', note.get('clip'), note.get('format'), self.repo / 'promo', self.cache)

    def md(self, note):
        return (self.store.session_dir(note['video']) / (note['id'] + '.md')).read_text()

    def test_clip_note_golden_text(self):
        """Pins the film-specific parts of a clip note's prompt byte for byte; the
        rest is the same text a single film's note gets (test_notes' golden)."""
        note = self.store.add('promo/film', '1x1', None, None, 'Make the credits warmer', None, clip='c')
        md = self.md(note)
        head, rest = md.split('\n## Ask first if truly unclear\n', 1)
        self.assertEqual(head, CLIP_NOTE_GOLDEN)
        self.assertIn('\n\n' + CLIP_NOTE_SCOPE_GOLDEN + 'Commit only changes to the video.', rest)
        self.assertNotIn('Change files only under promo.\n', md)

        single = NoteStore(Path(self.tmp.name, 'single'), FakeAgent(), context=DIRECTORY)
        plain = single.add('promo/film', '1x1', None, None, 'Make the credits warmer', None)
        plain_md = (single.session_dir('promo/film') / (plain['id'] + '.md')).read_text()
        film_part = md[md.index('## This note is about one clip'):md.index('## Ask first')]
        self.assertEqual(md.replace(film_part, '').replace(CLIP_NOTE_SCOPE_GOLDEN, 'Change files only under promo.\n'),
                         plain_md)

    def test_a_clip_note_names_its_act_and_both_neighbours(self):
        note = self.store.add('promo/film', '1x1', None, None, 'Slower', None, clip='boat')
        md = self.md(note)
        self.assertIn('clip 2 of 3, `boat`, in the act "The river": footage, promo/sources/boat.mp4 from frame '
                      '15 to 45, with no code of its own.', md)
        self.assertIn('Before it: clip 1, `a` (promo/clips/a); it cuts into this clip with a dissolve over 6 '
                      'frames.', md)
        self.assertIn('After it: clip 3, `c` (promo/clips/c); this clip cuts into it with a wipe to the left '
                      'over 6 frames.', md)
        self.assertIn('This clip is footage, so change only its own entry in promo/timeline.json', md)
        self.assertNotIn('PYTHONPATH', md)

    def test_a_whole_video_note(self):
        note = self.store.add('promo/film', '1x1', None, None, 'Add a clip about the bridge', None)
        md = self.md(note)
        self.assertIn('## A film made of clips', md)
        self.assertIn('1. `a`: promo/clips/a (act "The river")\n'
                      '2. `boat`: footage, promo/sources/boat.mp4 from frame 15 to 45 (act "The river")\n'
                      '3. `c`: promo/clips/c\n', md)
        self.assertIn('You may edit `promo/timeline.json`', md)
        self.assertIn('add, split or remove clip directories', md)
        self.assertIn('`python -m videobuilder assemble promo --check`', md)
        self.assertIn('''`python -c "from videobuilder.timeline_file import load; load('promo/timeline.json')"`''', md)
        self.assertIn('Read it first, and keep characters and the look consistent with it.', md)
        self.assertIn('Change the bible only when the note asks', md)
        self.assertIn('Change files only under promo.\n', md)
        self.assertNotIn('## This note is about one clip', md)

    def test_a_clip_gone_from_the_timeline_is_a_whole_video_note(self):
        note = self.store.add('promo/film', '1x1', None, None, 'Hm', None, clip='gone')
        md = self.md(note)
        self.assertIn('the clip `gone`, which is no longer in the timeline file', md)
        self.assertIn('Change files only under promo.\n', md)

    def test_no_bible_no_bible_section(self):
        git(self.repo, 'rm', '-rq', 'promo/bible')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'no bible')
        self.sha = git(self.repo, 'rev-parse', 'HEAD').strip()
        md = self.md(self.store.add('promo/film', '1x1', None, None, 'Hm', None, clip='c'))
        self.assertNotIn('## The bible', md)

    def test_a_timeline_that_does_not_validate(self):
        (self.repo / 'promo' / 'timeline.json').write_text('{"version": 1, "clips": [], "trim": 3}')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qam', 'broken')
        self.sha = git(self.repo, 'rev-parse', 'HEAD').strip()
        md = self.md(self.store.add('promo/film', '1x1', None, None, 'Fix it', None))
        self.assertIn('it does not validate:\ntimeline.json:', md)
        self.assertIn('Fix that first.', md)
        self.assertNotIn('written about the clip', md)

    def test_a_clip_note_on_a_timeline_that_does_not_validate_names_its_clip(self):
        (self.repo / 'promo' / 'timeline.json').write_text('{"version": 1, "clips": [], "trim": 3}')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qam', 'broken')
        self.sha = git(self.repo, 'rev-parse', 'HEAD').strip()
        md = self.md(self.store.add('promo/film', '1x1', None, None, 'Warmer', None, clip='c'))
        self.assertIn('Fix that first.', md)
        self.assertIn('This note was written about the clip `c`: once the timeline file validates', md)

    def test_retry_and_answer_keep_the_clip(self):
        agent = self.store.backend
        note = self.store.add('promo/film', '1x1', None, None, 'Hm', None, clip='c')
        agent.states[note['handle']] = AgentStatus('failed', 'no')
        self.store.list()
        self.assertEqual(self.store.retry(note['id'])['clip'], 'c')

    def test_a_note_without_a_clip_reads_back_with_clip_null(self):
        store = NoteStore(Path(self.tmp.name, 'old'))
        note = store.add('promo/film', '1x1', None, None, 'Hm', None)
        path = Path(store.dir, note['id'] + '.json')
        data = json.loads(path.read_text())
        data.pop('clip', None)
        path.write_text(json.dumps(data))  # a note saved before films had clips
        self.assertIsNone(store.get(note['id'])['clip'])
        self.assertEqual([n['clip'] for n in store.list()], [None])


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class NeighbourFrames(unittest.TestCase):
    """The last frame of the clip before and the first of the clip after, staged
    when there is something to grab them from, skipped quietly when not."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name, 'repo')
        self.repo.mkdir()
        make_media(self.repo / 'promo')
        self.sha = film_repo(self.repo)
        self.cache = assembly.ClipCache(Path(self.tmp.name, 'clips'))

    def brief(self, clip):
        return film_brief.brief(self.repo, self.sha, 'promo', clip, '1x1', self.repo / 'promo', self.cache)

    def stage(self, clip):
        brief, grabs = self.brief(clip)
        out = Path(self.tmp.name, 'attach-' + clip)
        out.mkdir()
        staged = {name: grab(out / name) for side, name, grab in grabs}
        return brief, grabs, out, staged

    def test_footage_frames_come_from_the_source(self):
        brief, grabs, out, staged = self.stage('c')
        self.assertEqual(staged, {film_brief.PREVIOUS_FRAME: True})
        # boat shows frames 15..44 of its source: its last is frame 44.
        expected = Path(self.tmp.name, 'expected.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.repo / 'promo/sources/boat.mp4'),
                        '-vf', r'select=eq(n\,44)', '-frames:v', '1', str(expected)], check=True)
        self.assertEqual(png_pixels(out / film_brief.PREVIOUS_FRAME), png_pixels(expected))

    def test_an_uncached_clip_is_skipped_and_a_cached_one_staged(self):
        brief, grabs = self.brief('boat')
        self.assertEqual(grabs, [])  # neither a nor c rendered yet
        self.assertIsNone(brief['before']['frame'])

        root = self.repo / 'promo'
        from videobuilder.timeline_file import load
        timeline = load(root / 'timeline.json')
        tree = GitTree(self.repo, self.sha, 'promo')  # how the editor keys its cache
        for cid in ('a', 'c'):
            clip = timeline.clip(cid)
            assembly.render_clip_local(root, clip, '1x1', self.cache.path(assembly.clip_key(tree, clip, '1x1'), '1x1'),
                                       jobs=1, log=QUIET)
        brief, grabs, out, staged = self.stage('boat')
        self.assertEqual(staged, {film_brief.PREVIOUS_FRAME: True, film_brief.NEXT_FRAME: True})
        # a's tail of 3 trims its last three frames: the film shows frame 26 of 30 last.
        a = self.cache.path(assembly.clip_key(tree, timeline.clip('a'), '1x1'), '1x1')
        for path, n in ((out / film_brief.PREVIOUS_FRAME, 26),
                        (out / film_brief.NEXT_FRAME, 0)):
            src = a if path.name == film_brief.PREVIOUS_FRAME else self.cache.path(
                assembly.clip_key(tree, timeline.clip('c'), '1x1'), '1x1')
            expected = Path(self.tmp.name, f'expected-{n}.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', rf'select=eq(n\,{n})',
                            '-frames:v', '1', str(expected)], check=True)
            self.assertEqual(png_pixels(path), png_pixels(expected), path.name)

    def test_the_prompt_names_only_the_staged_frames(self):
        store = NoteStore(Path(self.tmp.name, 'notes'), FakeAgent(), context=DIRECTORY)

        class Staging:
            def expire(self):
                pass

            def stage(self, note, frame=None, force=False):
                path = store.session_dir(note['video']) / ('attachments-' + note['id'])
                path.mkdir(exist_ok=True)
                return str(path) if force else None
        store.attachments = Staging()
        store.film = lambda video, note, state: self.brief(note.get('clip'))
        note = store.add('promo/film', '1x1', None, None, 'Warmer', None, clip='c')
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('Its last frame, as the film shows it, is /attachments/previous-clip-last-frame.png.', md)
        self.assertIn('open /attachments/previous-clip-last-frame.png before you start.', md)
        self.assertTrue(Path(store.backend.submitted[0]['attach_dir'], film_brief.PREVIOUS_FRAME).is_file())
        self.assertNotIn('next-clip-first-frame', md)


def png_pixels(path):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                          capture_output=True, check=True).stdout


class ClipField(TempProject):
    """POST /api/notes `clip`: validated against timeline.json at main."""
    start = fixtures.API.start
    post = fixtures.API.post
    get = fixtures.API.get

    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.start()

    def test_clip_on_a_film_and_not(self):
        status, body = self.post('/api/notes', {'video': 'promo/film', 'text': 'x', 'clip': 'a'})
        self.assertEqual(status, 400, body)
        self.assertIn('not a film of clips', body['error'])
        status, plain = self.post('/api/notes', {'video': 'promo/film', 'text': 'whole'})
        self.assertEqual(status, 200, plain)
        self.assertIsNone(plain['clip'])

        write_film(self.root / 'promo', three_clips(), pin=False)
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'a film of clips')
        for bad in ('nope', 3, ['a']):
            status, body = self.post('/api/notes', {'video': 'promo/film', 'text': 'x', 'clip': bad})
            self.assertEqual(status, 400, (bad, body))
        status, note = self.post('/api/notes', {'video': 'promo/film', 'text': 'warmer', 'clip': 'c'})
        self.assertEqual(status, 200, note)
        self.assertEqual(note['clip'], 'c')
        notes = self.get('/api/notes?video=promo/film')['notes']
        self.assertEqual([n['clip'] for n in notes], [None, 'c'])
        self.assertEqual(self.get(f"/api/notes/{note['id']}")['clip'], 'c')
        md = (self.editor.notes.session_dir('promo/film') / (plain['id'] + '.md')).read_text()
        self.assertNotIn('film made of clips', md)  # a single film's note, as before
        self.editor.notes.update(self.editor.notes.get(plain['id']), state='failed')
        self.editor.notes.list()  # the whole-video note was a single film's: let the clip note go next
        md = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('This note is about clip 3 of 3, `c`', md)
        self.assertIn('Change files only under promo/clips/c.', md)

        # A clip only on a draft, not at main, is refused.
        git(self.root, 'checkout', '-qb', 'side')
        t = three_clips()
        t['clips'].append({'id': 'd', 'dir': 'clips/c'})
        (self.root / 'promo' / 'timeline.json').write_text(json.dumps(t))
        git(self.root, 'commit', '-qam', 'd')
        git(self.root, 'checkout', '-q', 'main')
        status, body = self.post('/api/notes', {'video': 'promo/film', 'text': 'x', 'clip': 'd'})
        self.assertEqual(status, 400, body)


class AssembleCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_film(self.root, three_clips())

    def check(self):
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parent.parent)}
        return subprocess.run([sys.executable, '-m', 'videobuilder', 'assemble', str(self.root), '--check'],
                              capture_output=True, text=True, env=env)

    def test_check_validates_without_rendering(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('timeline.json: ok, 3 clips', result.stdout)
        self.assertIn('not on disk here (fine if it is an upload): sources/boat.mp4', result.stderr)
        self.assertFalse((self.root / '.vb-cache').exists())

        (self.root / 'clips' / 'c' / 'film.py').unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clip "c": no film file clips/c/film.py', result.stderr)

        (self.root / 'timeline.json').write_text(json.dumps({**three_clips(), 'trim': 1}))
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('trim', result.stderr)


if __name__ == '__main__':
    unittest.main()

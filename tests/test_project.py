"""A project's videos, found; and direct edits, each committed to git."""
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from videobuilder import edits, project
from videobuilder.project import Project, discover

# 15 frames a beat; intro and body roll, the group's children roll, close doesn't.
FILM = textwrap.dedent('''
    import videobuilder as vb
    T = vb.Timeline(vb.Grid(fps=30, bpm=120), [
        vb.Segment('intro', 0, 4, dict(title='Hello', n=3)),
        vb.Segment('body', 4, 8, dict(line='Body copy')),
        vb.Segment('cuts', 8, 12, dict(head='Cuts'), children=vb.sequence(8, [('c1', 2), ('c2', 2)])),
        vb.Segment('close', 12, 14),
    ], end=14)
    COLOURS = {'intro': '#f00', 'body': '#0f0', 'c1': '#00f', 'c2': '#ff0', 'close': '#0ff'}
    def draw(n, cv):
        cv.rect(0, 0, cv.width, cv.height, COLOURS[T.at(n)[0].name])
    FILM = vb.Film(draw=draw, timeline=T, formats=('16x9', '1x1'))
''')


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def make_repo(d):
    git(d, 'init', '-q')
    git(d, 'config', 'user.name', 'Reviewer')
    git(d, 'config', 'user.email', 'reviewer@example.com')
    git(d, 'config', 'commit.gpgsign', 'false')


class TempProject(unittest.TestCase):
    """A project with one video, `promo/film`, optionally in a git repo."""
    repo = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name, 'project')
        (self.root / 'promo').mkdir(parents=True)
        self.film = self.root / 'promo' / 'film.py'
        self.film.write_text(FILM)
        self.toml = self.root / 'promo' / 'film.edits.toml'
        (self.root / 'README.md').write_text('a project\n')
        if self.repo:
            make_repo(self.root)
            git(self.root, 'add', '-A')
            git(self.root, 'commit', '-qm', 'init')

    def tearDown(self):
        self.tmp.cleanup()

    def log(self):
        return git(self.root, 'log', '--format=%s').splitlines()

    def files_in(self, rev='HEAD'):
        return git(self.root, 'show', '--name-only', '--format=', rev).split()


class Discovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_the_rule(self):
        film = 'import videobuilder as vb\nT = vb.Timeline(vb.Grid(), [], end=0)\nFILM = vb.Film(draw=None, timeline=T)\n'
        self.write('launch/film.py', film)
        self.write('launch/storyboard.py', 'SEGMENTS = []\n')                      # a helper: no FILM
        self.write('promo/promo.py', 'from videobuilder import Film, Timeline\nFILM: Film = make(Timeline)\n')
        self.write('promo/old.py', 'import videobuilder as vb\nFILM = vb.Film(draw=None, fps=30, frames=3)\n')  # no Timeline
        self.write('promo/broken.py', 'FILM = (\n')
        self.write('promo/nested.py', 'def f():\n    FILM = Timeline()\n')       # FILM not at module level
        for skipped in ('tests/film.py', 'vendor/lib/film.py', '.hidden/film.py', 'node_modules/x/film.py',
                        'state/film.py'):
            self.write(skipped, film)
        got = discover(self.root, skip=[self.root / 'state'])
        self.assertEqual([v.id for v in got], ['launch/film', 'promo/promo'])
        self.assertEqual(got[0].path, str(self.root / 'launch' / 'film.py'))
        self.assertEqual(got[0].to_json(str(self.root)),
                         {'id': 'launch/film', 'path': 'launch/film.py', 'edits': 'launch/film.edits.toml'})

    def test_videobuilder_toml_lists_them(self):
        self.write('a/one.py', 'x = 1\n')  # listed films aren't read for FILM
        self.write('b/two.py', 'x = 2\n')
        self.write('c/film.py', 'FILM = Timeline()\n')  # found by the rule, but not listed
        self.write('videobuilder.toml', '[editor]\nvideos = ["b/two.py", "a/one.py"]\n')
        self.assertEqual([v.id for v in discover(self.root)], ['a/one', 'b/two'])
        self.write('videobuilder.toml', '[editor]\nvideos = ["../outside.py"]\n')
        with self.assertRaisesRegex(ValueError, 'outside the project'):
            discover(self.root)
        self.write('videobuilder.toml', '[editor]\nvideos = ["a/missing.py"]\n')
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            discover(self.root)
        self.write('videobuilder.toml', '[editor]\nvideos = "a/one.py"\n')
        with self.assertRaisesRegex(ValueError, 'list of film paths'):
            discover(self.root)

    def test_the_examples(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual([v.id for v in discover(root / 'examples')],
                         ['benchmark', 'capabilities/beat-lock', 'capabilities/counting-numbers',
                          'capabilities/eased-entrances', 'capabilities/every-format', 'capabilities/footage-with-sound',
                          'capabilities/overlap-transitions', 'showcase', 'tour'])


class Committing(TempProject):
    def setUp(self):
        super().setUp()
        self.project = Project(self.root)

    def test_roll_commits_only_the_edits_file(self):
        (self.root / 'README.md').write_text('changed, not committed\n')
        (self.root / 'staged.txt').write_text('staged by someone\n')
        git(self.root, 'add', 'staged.txt')
        r = self.project.edit('promo/film', 'roll', 'intro', 6.5)
        self.assertEqual(r['message'], 'edit(promo/film): roll intro to beat 6.5')
        self.assertIsNone(r['warning'])
        self.assertTrue(r['changed'])
        self.assertEqual(r['commit'], git(self.root, 'rev-parse', 'HEAD').strip())
        self.assertEqual(r['undo'], {'op': 'roll', 'segment': 'intro', 'value': 4})
        self.assertEqual(self.log()[0], 'edit(promo/film): roll intro to beat 6.5')
        self.assertEqual(self.files_in(), ['promo/film.edits.toml'])
        self.assertEqual(self.toml.read_text(), '[segments.intro]\nuntil = 6.5\n')
        status = git(self.root, 'status', '--porcelain').splitlines()
        self.assertEqual(sorted(status), sorted([' M README.md', 'A  staged.txt']))  # left as they were
        author = git(self.root, 'log', '-1', '--format=%an <%ae>').strip()
        self.assertEqual(author, 'Reviewer <reviewer@example.com>')  # from git config

    def test_copy_then_undo_restores_and_commits_again(self):
        r = self.project.edit('promo/film', 'copy', 'intro', 'New "title"', key='title')
        self.assertEqual(r['message'], 'edit(promo/film): copy intro.title')
        self.assertEqual(edits.Edits.read(str(self.toml)).segments, {'intro': {'data': {'title': 'New "title"'}}})
        r = self.project.undo('promo/film')
        self.assertEqual(r['message'], 'edit(promo/film): copy intro.title (undo)')
        self.assertIsNotNone(r['commit'])
        self.assertFalse(self.toml.exists())  # back to the film's own copy: no edits left
        self.assertEqual(self.log()[:2], ['edit(promo/film): copy intro.title (undo)', 'edit(promo/film): copy intro.title'])
        self.assertEqual(self.files_in(), ['promo/film.edits.toml'])  # the deletion, committed
        with self.assertRaisesRegex(ValueError, 'nothing to undo'):
            self.project.undo('promo/film')

    def test_undo_reverses_a_roll_over_an_earlier_edit(self):
        self.project.edit('promo/film', 'roll', 'intro', 6)
        self.project.edit('promo/film', 'roll', 'intro', 3)
        self.project.undo('promo/film')
        self.assertEqual(self.toml.read_text(), '[segments.intro]\nuntil = 6\n')
        self.assertEqual(self.log()[0], 'edit(promo/film): roll intro to beat 6 (undo)')

    def test_refusals_change_nothing(self):
        self.project.edit('promo/film', 'roll', 'intro', 6)
        before, head = self.toml.read_bytes(), self.log()
        for args, pattern in ((('roll', 'intro', 6.25), 'half-beat'), (('roll', 'cuts', 13), 'group'),
                              (('roll', 'close', 13), 'no next segment'), (('roll', 'nope', 2), "'nope'"),
                              (('roll', 'intro', '6'), 'number of beats'),
                              (('copy', 'intro', 'x'), 'data.n is int'),
                              (('copy', 'intro', 'x', 'missing'), "no key 'missing'")):
            op, seg, value, *key = args
            key = key[0] if key else ('n' if op == 'copy' else None)
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, pattern):
                self.project.edit('promo/film', op, seg, value, key=key)
        self.assertEqual((self.toml.read_bytes(), self.log()), (before, head))
        self.assertEqual(self.project.last['promo/film'], {'op': 'roll', 'segment': 'intro', 'value': 4})
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_the_same_value_again_is_no_change_and_no_commit(self):
        self.project.edit('promo/film', 'roll', 'intro', 6)
        r = self.project.edit('promo/film', 'roll', 'intro', 6)
        self.assertEqual((r['changed'], r['commit'], r['warning']), (False, None, None))
        self.assertEqual(len(self.log()), 2)

    def test_uncommitted_changes_to_the_edits_file_are_not_committed(self):
        self.toml.write_text('[segments.c1]\nuntil = 9\n')  # by hand, outside the editor
        r = self.project.edit('promo/film', 'roll', 'intro', 3)
        self.assertIsNone(r['commit'])
        self.assertIn('uncommitted changes', r['warning'])
        self.assertEqual(self.toml.read_text(), '[segments.c1]\nuntil = 9\n\n[segments.intro]\nuntil = 3\n')
        self.assertEqual(self.log(), ['init'])
        self.assertEqual(self.project.git_info('promo/film'), {'repo': True, 'state': 'dirty'})

    def test_a_commit_git_refuses_is_a_warning(self):
        hooks = self.root / '.git' / 'hooks'
        git(self.root, 'config', 'core.hooksPath', str(hooks))  # over any global hooksPath
        (hooks / 'pre-commit').write_text('#!/bin/sh\necho no commits today >&2\nexit 1\n')
        os.chmod(hooks / 'pre-commit', 0o755)
        r = self.project.edit('promo/film', 'roll', 'intro', 3)
        self.assertIsNone(r['commit'])
        self.assertIn('no commits today', r['warning'])
        self.assertTrue(self.toml.exists())
        self.assertEqual(git(self.root, 'diff', '--cached', '--name-only'), '')  # nothing left staged

    def test_videos_are_found_again_when_asked_for_an_unknown_one(self):
        self.assertEqual([v.id for v in self.project.videos()], ['promo/film'])
        (self.root / 'launch').mkdir()
        (self.root / 'launch' / 'film.py').write_text(FILM)
        self.assertEqual(self.project.video('launch/film').path, str(self.root / 'launch' / 'film.py'))
        (self.root / 'launch' / 'film.py').unlink()
        with self.assertRaises(KeyError):
            self.project.video('launch/film')
        (self.root / 'videobuilder.toml').write_text('[editor]\nvideos = []\n')  # a list is the truth
        self.assertEqual(self.project.videos(), [])
        with self.assertRaises(KeyError):
            self.project.video('promo/film')

    def test_unknown_video(self):
        with self.assertRaises(KeyError):
            self.project.edit('nope', 'roll', 'intro', 3)


class NotARepo(TempProject):
    repo = False

    def test_edits_are_saved_with_a_warning(self):
        if project.git_root(str(self.root)) is not None:
            self.skipTest('the temp dir is inside a git work tree')
        p = Project(self.root)
        r = p.edit('promo/film', 'roll', 'intro', 6)
        self.assertIsNone(r['commit'])
        self.assertIn('not a git repository', r['warning'])
        self.assertEqual(self.toml.read_text(), '[segments.intro]\nuntil = 6\n')
        self.assertEqual(p.git_info('promo/film'), {'repo': False, 'state': 'none'})


if __name__ == '__main__':
    unittest.main()

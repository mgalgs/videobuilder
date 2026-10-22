"""Every technique in `videobuilder/techniques/`, checked one by one, plus the
registry itself.

`EachTechnique` has one test per technique module, named after the module
(the id with `-` as `_`), so one technique checks alone with:

    python3 -m unittest tests.test_techniques.EachTechnique.test_<id with - as _>

e.g. `python3 -m unittest tests.test_techniques.EachTechnique.test_bounce_ease_out`.
That command passing is a new technique's acceptance. Each test imports only
its own module, so a broken technique fails its own test, not its
neighbours'. It checks: the record is valid; its id matches the file and its
family the package; every `api` name resolves; the demo builds a short 16:9
Film; and a few frames rendered at a small scale are not all the same (a
`sound` technique must carry audio instead).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder import techniques
from videobuilder.techniques import Technique
from videobuilder.techniques.schema import FAMILIES, module_name

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / 'videobuilder' / 'techniques'

SCALE = 0.1      # frames are rendered this small: enough to see movement, cheap over ~900 techniques
SAMPLES = 5      # frames sampled evenly across each demo
MIN_SECONDS, MAX_SECONDS = 1.5, 5.0
WORKED = ('ease-out-back', 'bounce-ease-out', 'dip-to-black', 'scramble-decode')


def check(case, family, name):
    t = techniques.load(family, name)   # validates the record, the id/file and family/package, and `api`
    case.assertIsInstance(t, Technique)
    case.assertEqual(module_name(t.id), name)
    case.assertEqual(t.family, family)
    for obj in t.resolve_api():
        case.assertIsNotNone(obj)
    film = t.demo()
    case.assertIsInstance(film, vb.Film, f'{t.id}: demo() must return a videobuilder.Film')
    fmt = film.format()
    case.assertEqual((fmt.width * 9, fmt.name), (fmt.height * 16, '16x9'), f'{t.id}: demo must be 16x9')
    seconds = film.frames / film.fps
    case.assertTrue(MIN_SECONDS <= seconds <= MAX_SECONDS,
                    f'{t.id}: demo is {seconds:.2f}s; keep it about 2 to 4 seconds')
    if t.family == 'sound':
        case.assertTrue(film.audio is not None or film.sounds, f'{t.id}: a sound technique must carry audio')
        return
    picks = sorted({round(i * (film.frames - 1) / (SAMPLES - 1)) for i in range(SAMPLES)})
    frames = {film.frame(n, scale=SCALE).bgra() for n in picks}
    case.assertGreater(len(frames), 1, f'{t.id}: frames {picks} are all identical; the demo must move')


class EachTechnique(unittest.TestCase):
    """One `test_<module>` per technique module, added below."""


def _add(family, name):
    def test(self):
        check(self, family, name)
    test.__doc__ = f'{family}/{name}.py'
    setattr(EachTechnique, f'test_{name}', test)


for _family, _name in techniques.modules():
    _add(_family, _name)


class Registry(unittest.TestCase):
    def test_every_family_is_a_package(self):
        for fam in FAMILIES:
            self.assertTrue((PKG / fam / '__init__.py').is_file(), fam)

    def test_the_worked_examples_are_there(self):
        self.assertLessEqual(set(WORKED), set(techniques.ids()))

    def test_ids_are_unique_across_families(self):
        names = [name for _, name in techniques.modules()]
        self.assertEqual(len(names), len(set(names)), 'two families have a technique with the same id')

    def test_one_test_per_module(self):
        tests = {n for n in dir(EachTechnique) if n.startswith('test_')}
        self.assertEqual(tests, {f'test_{name}' for _, name in techniques.modules()})

    def test_helpers_are_not_techniques(self):
        names = {name for _, name in techniques.modules()}
        self.assertFalse(any(n.startswith('_') for n in names))

    def test_get_and_family_filter(self):
        self.assertEqual(techniques.get('dip-to-black').family, 'transitions')
        with self.assertRaises(KeyError):
            techniques.get('no-such-technique')
        self.assertEqual({t.family for t in techniques.catalog('principles')}, {'principles'})
        with self.assertRaises(ValueError):
            techniques.catalog('nope')

    def test_index_groups_by_family_then_group(self):
        md = techniques.index_markdown()
        self.assertLess(md.index('## principles'), md.index('### Easing'))
        self.assertLess(md.index('### Easing'), md.index('## typography'))
        self.assertLess(md.index('## typography'), md.index('## transitions'))
        for t in techniques.catalog():
            self.assertIn(f'`{t.id}`', md)
            self.assertIn(t.definition, md)
            for a in t.api:
                self.assertIn(a, md)
        data = techniques.index_data()
        self.assertEqual(json.loads(techniques.index_json()), data)
        fams = [f['family'] for f in data['families']]
        self.assertEqual(fams, [f for f in FAMILIES if f in fams])  # FAMILIES order, whichever have techniques
        only = techniques.index_data('transitions')
        self.assertEqual([f['family'] for f in only['families']], ['transitions'])

    def test_skill_links_the_reference(self):
        self.assertTrue((ROOT / 'skill' / 'make-a-video' / 'reference' / 'techniques.md').is_file())
        self.assertIn('reference/techniques.md', (ROOT / 'skill' / 'make-a-video' / 'SKILL.md').read_text())

    def test_no_outside_sources_named(self):
        # Definitions and phrasings are our own words; nothing links or credits a catalogue.
        for path in PKG.rglob('*.py'):
            text = path.read_text()
            self.assertNotRegex(text, r'https?://|www\.', path.name)


class Record(unittest.TestCase):
    def make(self, **kw):
        base = dict(id='a-thing', name='A Thing', family='principles', group='Easing',
                    definition='It moves.', phrasings=('one way', 'another way'),
                    api=('videobuilder.linear',), demo=lambda: None)
        return Technique(**{**base, **kw})

    def test_valid_record_normalises_lists(self):
        t = self.make(phrasings=['one way', 'another way'], related=['other-thing'])
        self.assertEqual(t.phrasings, ('one way', 'another way'))
        self.assertEqual(t.related, ('other-thing',))

    def test_rejects(self):
        bad = [dict(id='A_Thing'), dict(id='a--thing'), dict(id='3d-flip'), dict(family='nope'), dict(group=''),
               dict(definition='no full stop'), dict(definition='x' * 300 + '.'),
               dict(phrasings=('only one',)), dict(phrasings='a string, not a tuple'),
               dict(phrasings=('same', 'same')), dict(related=('Not Kebab',)), dict(related=('a-thing',)),
               dict(api=()), dict(api=('ease_out_back',)), dict(demo='not callable'), dict(aliases=('',))]
        for kw in bad:
            with self.subTest(**{k: str(v)[:20] for k, v in kw.items()}), self.assertRaises(ValueError):
                self.make(**kw)

    def test_api_must_resolve(self):
        with self.assertRaisesRegex(LookupError, 'no_such_thing'):
            self.make(api=('videobuilder.no_such_thing',)).resolve_api()
        self.assertIs(self.make().resolve_api()[0], vb.linear)


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'videobuilder', 'techniques', *args], cwd=ROOT,
                          capture_output=True, text=True)


class Cli(unittest.TestCase):
    def test_index(self):
        out = cli('index')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, techniques.index_markdown())
        out = cli('index', '--json', '--family', 'typography')
        self.assertEqual(json.loads(out.stdout), techniques.index_data('typography'))
        self.assertNotEqual(cli('index', '--family', 'nope').returncode, 0)

    def test_build_one_writes_clip_poster_and_gallery(self):
        with tempfile.TemporaryDirectory() as d:
            out = cli('build', '--out', d, '--only', 'dip-to-black', '--jobs', '2')
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sorted(os.listdir(d)), ['dip-to-black.jpg', 'dip-to-black.mp4', 'index.html'])
            page = Path(d, 'index.html').read_text()
            self.assertIn('src="dip-to-black.mp4"', page)
            self.assertIn('poster="dip-to-black.jpg"', page)
            self.assertIn('prefers-color-scheme: dark', page)
            self.assertNotIn('bounce-ease-out', page)
            self.assertNotEqual(cli('build', '--out', d, '--only', 'no-such-id').returncode, 0)

    def test_gallery_escapes_and_groups(self):
        from videobuilder.techniques.gallery import gallery_html
        page = gallery_html(techniques.catalog())
        self.assertLess(page.index('id="family-principles"'), page.index('id="family-transitions"'))
        self.assertNotIn('http', page)


class OneTechniqueAlone(unittest.TestCase):
    def test_documented_command_runs_one_technique(self):
        proc = subprocess.run([sys.executable, '-m', 'unittest', '-v',
                               'tests.test_techniques.EachTechnique.test_bounce_ease_out'],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Ran 1 test', proc.stderr)


if __name__ == '__main__':
    unittest.main()

"""Every capability in `videobuilder/capabilities/<family>/`, checked one by
one, plus the registry itself.

`EachCapability` has one test per capability module, named after the module
(the id with `-` as `_`), so one capability checks alone with:

    python3 -m unittest tests.test_capabilities_registry.EachCapability.test_<id with - as _>

e.g. `python3 -m unittest tests.test_capabilities_registry.EachCapability.test_bounce_ease_out`.
That command passing is a new capability's acceptance. Each test imports only
its own module, so a broken capability fails its own test, not its
neighbours'. It checks: the record is valid; its id matches the file and its
family the package; every `api` name resolves; the demo builds a short 16:9
Film (a worked example film, `demo=Example(...)`, keeps its own length and
format: see schema.Example); and a few frames rendered at a small scale are
not all the same (a `sound` capability must carry audio instead).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import videobuilder as vb
from videobuilder.capabilities import registry
from videobuilder.capabilities.schema import FAMILIES, Capability, module_name

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / 'videobuilder' / 'capabilities'

SCALE = 0.1      # frames are rendered this small: enough to see movement, cheap over ~900 capabilities
SAMPLES = 5      # frames sampled evenly across each demo
MIN_SECONDS, MAX_SECONDS = 1.5, 5.0
WORKED = ('ease-out-back', 'bounce-ease-out', 'dip-to-black', 'scramble-decode')


def check(case, family, name):
    id_ = name.replace('_', '-')
    merged = registry.merged_into(id_)
    if merged is not None:   # gave up CAPABILITY for MERGED_INTO: check the chain lands somewhere real
        case.assertIsNone(registry.load(family, name))
        case.assertIn(merged, registry.ids())
        case.assertIn(id_, registry.get(merged).old_ids)
        return
    t = registry.load(family, name)   # validates the record, the id/file and family/package, and `api`
    case.assertIsInstance(t, Capability)
    case.assertEqual(module_name(t.id), name)
    case.assertEqual(t.family, family)
    for obj in t.resolve_api():
        case.assertIsNotNone(obj)
    film = t.demo()
    case.assertIsInstance(film, vb.Film, f'{t.id}: demo() must return a videobuilder.Film')
    if t.is_example:
        case.assertTrue((ROOT / t.demo.path).is_file(), t.demo.path)
    else:   # the short-demo rule: every capability but a worked example film (schema.Example)
        fmt = film.format()
        case.assertEqual((fmt.width * 9, fmt.name), (fmt.height * 16, '16x9'), f'{t.id}: demo must be 16x9')
        seconds = film.frames / film.fps
        case.assertTrue(MIN_SECONDS <= seconds <= MAX_SECONDS,
                        f'{t.id}: demo is {seconds:.2f}s; keep it about 2 to 4 seconds')
    if t.family == 'sound':
        case.assertTrue(film.audio is not None or film.sounds, f'{t.id}: a sound capability must carry audio')
        return
    picks = sorted({round(i * (film.frames - 1) / (SAMPLES - 1)) for i in range(SAMPLES)})
    frames = {film.frame(n, scale=SCALE).bgra() for n in picks}
    case.assertGreater(len(frames), 1, f'{t.id}: frames {picks} are all identical; the demo must move')


class EachCapability(unittest.TestCase):
    """One `test_<module>` per capability module, added below."""


def _add(family, name):
    def test(self):
        check(self, family, name)
    test.__doc__ = f'{family}/{name}.py'
    setattr(EachCapability, f'test_{name}', test)


for _family, _name in registry.modules():
    _add(_family, _name)


class Registry(unittest.TestCase):
    def test_every_family_is_a_package(self):
        for fam in FAMILIES:
            self.assertTrue((PKG / fam / '__init__.py').is_file(), fam)

    def test_the_worked_examples_are_there(self):
        self.assertLessEqual(set(WORKED), set(registry.ids()))

    def test_ids_are_unique_across_families(self):
        names = [name for _, name in registry.modules()]
        self.assertEqual(len(names), len(set(names)), 'two families have a capability with the same id')

    def test_no_id_collides_with_an_old_id_or_a_showcase_file(self):
        # clip_file() rewrites old ids, and shares its directory with SHOWCASE_FILES -- a
        # collision there would silently shadow or overwrite a capability's clip.
        from videobuilder import capabilities
        self.assertFalse(set(registry.ids()) & set(capabilities.old_ids()))
        self.assertFalse(set(registry.ids()) & set(capabilities.SHOWCASE_FILES))

    def test_ids_are_the_loaded_records_ids(self):
        self.assertEqual(registry.ids(), tuple(t.id for t in registry.catalog()))

    def test_every_member_is_a_capability_in_one_group_only(self):
        seen = {}
        for t in registry.catalog():
            if not t.members:
                continue
            headings = {h for _, h, _ in t.members.kinds}
            for i in t.members.ids:
                with self.subTest(group=t.id, member=i):
                    m = registry.get(i)                # KeyError if it isn't one
                    self.assertNotIn(i, seen)
                    seen[i] = t.id
                    self.assertFalse(m.category)       # its section is its group's
                    self.assertFalse(m.members)
                    if headings:
                        self.assertIn(m.group, headings)

    def test_one_test_per_module(self):
        tests = {n for n in dir(EachCapability) if n.startswith('test_')}
        self.assertEqual(tests, {f'test_{name}' for _, name in registry.modules()})

    def test_helpers_are_not_capabilities(self):
        names = {name for _, name in registry.modules()}
        self.assertFalse(any(n.startswith('_') for n in names))

    def test_get_and_family_filter(self):
        self.assertEqual(registry.get('dip-to-black').family, 'transitions')
        with self.assertRaises(KeyError):
            registry.get('no-such-capability')
        self.assertEqual({t.family for t in registry.catalog('principles')}, {'principles'})
        with self.assertRaises(ValueError):
            registry.catalog('nope')

    def test_index_groups_by_family_then_group(self):
        md = registry.index_markdown()
        self.assertLess(md.index('## principles'), md.index('### Easing'))
        self.assertLess(md.index('### Easing'), md.index('## typography'))
        self.assertLess(md.index('## typography'), md.index('## transitions'))
        for t in registry.catalog():
            self.assertIn(f'`{t.id}`', md)
            self.assertIn(t.definition, md)
            for a in t.api:
                self.assertIn(a, md)
        data = registry.index_data()
        self.assertEqual(json.loads(registry.index_json()), data)
        fams = [f['family'] for f in data['families']]
        self.assertEqual(fams, [f for f in FAMILIES if f in fams])  # FAMILIES order, whichever have capabilities
        only = registry.index_data('transitions')
        self.assertEqual([f['family'] for f in only['families']], ['transitions'])

    def test_index_related_resolves_through_the_merge(self):
        # breathing-idle's hand-written `related` still names scale-pulse by its old id (now
        # breathing-idle's own old id, since scale-pulse merged into it): that must not come
        # back as a self-reference in the index.
        data = registry.index_data()
        by_id = {t['id']: t for fam in data['families'] for g in fam['groups'] for t in g['capabilities']}
        self.assertNotIn('scale-pulse', by_id['breathing-idle']['related'])
        self.assertNotIn('breathing-idle', by_id['breathing-idle']['related'])
        # air-drag names momentum-fling, which merged into friction-deceleration: the index
        # must point at the survivor, not a dangling id with no entry of its own.
        self.assertIn('friction-deceleration', by_id['air-drag']['related'])
        self.assertNotIn('momentum-fling', by_id['air-drag']['related'])
        old = {o for t in registry.catalog() for o in t.old_ids}
        for t in by_id.values():
            for r in t['related']:
                self.assertNotIn(r, old, f'{t["id"]}: related id {r!r} is a merged-away id')

    def test_no_outside_sources_named(self):
        # Definitions and phrasings are our own words; nothing links or credits a catalogue. The one
        # place a link may sit is the record's own `source=Source(...)`: the post it came from.
        for fam, name in registry.modules():
            text = (PKG / fam / f'{name}.py').read_text()
            text = re.sub(r'\n    source=Source\((?:[^()]|\([^()]*\))*\),', '', text)
            self.assertNotRegex(text, r'https?://|www\.', f'{fam}/{name}.py')


class MergedModules(unittest.TestCase):
    """A module trades CAPABILITY for MERGED_INTO when it was folded into
    another capability (see registry.py's module docstring); the chain it
    names must land on a real capability."""

    def tearDown(self):
        registry._all.cache_clear()   # undo any corruption from a mocked _merge_targets below

    def test_a_target_naming_nothing_real_is_an_error(self):
        with mock.patch.object(registry, '_merge_targets', lambda: {'ease-out-back': 'no-such-id'}):
            registry._all.cache_clear()
            with self.assertRaisesRegex(ValueError, 'no-such-id'):
                registry._all()

    def test_a_cycle_is_an_error(self):
        with mock.patch.object(registry, '_merge_targets', lambda: {'a': 'b', 'b': 'a'}):
            with self.assertRaisesRegex(ValueError, 'cycle'):
                registry._resolve_merge('a')

    def test_a_chain_resolves_to_its_final_capability(self):
        self.assertEqual(registry.merged_into('multiplane-camera'), 'parallax-scene')
        self.assertEqual(registry.merged_into('parallax-layers'), 'parallax-scene')
        self.assertIsNone(registry.merged_into('parallax-scene'))

    def test_a_merged_id_is_an_old_id_of_its_survivor_and_still_resolves(self):
        from videobuilder import capabilities
        self.assertIn('shape-morph', registry.get('outline-morph').old_ids)
        self.assertEqual(capabilities.resolve('shape-morph'), 'outline-morph')
        self.assertEqual(capabilities.get('shape-morph').id, 'outline-morph')
        with self.assertRaises(KeyError):
            registry.get('shape-morph')


class MergedModuleImports(unittest.TestCase):
    """A merged module trades its `CAPABILITY` for `MERGED_INTO`, but its own
    code stays, because a film may still import it (registry.py's module
    docstring). One import per family that has a merge, so a later cleanup
    that deletes a merged module's now-record-less helpers fails here first."""

    def test_broadcast_flight_arc(self):
        from videobuilder.capabilities.broadcast.flight_arc import flight_arc
        self.assertTrue(callable(flight_arc))

    def test_camera_parallax_layers(self):
        from videobuilder.capabilities.camera.parallax_layers import draw
        self.assertTrue(callable(draw))

    def test_particles_water_caustics(self):
        from videobuilder.capabilities.particles.water_caustics import caustic_field
        self.assertTrue(callable(caustic_field))

    def test_principles_underdamped_spring(self):
        from videobuilder.capabilities.principles.underdamped_spring import coil
        self.assertTrue(callable(coil))

    def test_shapes_brush_stroke_paint_reveal(self):
        from videobuilder.capabilities.shapes.brush_stroke_paint_reveal import brush_reveal
        self.assertTrue(callable(brush_reveal))

    def test_sound_ducking(self):
        from videobuilder.capabilities.sound.ducking import gain
        self.assertTrue(callable(gain))

    def test_transitions_zoom_through(self):
        from videobuilder.capabilities.transitions.zoom_through import zoom_through
        self.assertTrue(callable(zoom_through))

    def test_typography_terminal_line_print(self):
        from videobuilder.capabilities.typography.terminal_line_print import draw
        self.assertTrue(callable(draw))

    def test_ui_cursor_particle_trail(self):
        from videobuilder.capabilities.ui.cursor_particle_trail import trail_particles
        self.assertTrue(callable(trail_particles))

    def test_vfx_linocut(self):
        from videobuilder.capabilities.vfx.linocut import linocut
        self.assertTrue(callable(linocut))


class PosterFrame(unittest.TestCase):
    """`registry.poster_frame` (used by both `capabilities.build_registry` and
    `capabilities.gallery`): a transition's poster lands in the middle of its
    demo's move, wherever that move actually falls, instead of a frame that
    may land before it starts or after it has already finished."""

    def test_lands_inside_the_move_whichever_default_would_have_missed_it(self):
        # whip-pan's move (start=1.8s, length=0.6s -> frames 54..72) starts after
        # the demo's middle frame (45): the old frames // 2 default landed before
        # the whip even begins.
        t = registry.get('whip-pan')
        film = t.demo()
        self.assertEqual(registry.poster_frame(t, film, film.frames // 2), 63)
        self.assertTrue(54 < 63 < 72)

        # punch-in's move (start=1.0s, length=0.8s -> frames 30..54) ends well
        # before 70% of the demo (63): the old gallery default landed on the
        # held close-up, after the punch had already settled.
        t = registry.get('punch-in')
        film = t.demo()
        gallery_default = min(film.frames - 1, int(film.frames * 0.7))
        self.assertEqual(gallery_default, 62)
        self.assertEqual(registry.poster_frame(t, film, gallery_default), 42)
        self.assertTrue(30 < 42 < 54)

    def test_non_transition_keeps_its_old_default(self):
        t = registry.get('ease-out-back')
        self.assertNotEqual(t.family, 'transitions')
        film = t.demo()
        self.assertEqual(registry.poster_frame(t, film, film.frames // 2), film.frames // 2)
        gallery_default = min(film.frames - 1, int(film.frames * 0.7))
        self.assertEqual(registry.poster_frame(t, film, gallery_default), gallery_default)


class Record(unittest.TestCase):
    def make(self, **kw):
        base = dict(id='a-thing', name='A Thing', family='principles', group='Easing',
                    definition='It moves.', phrasings=('one way', 'another way'),
                    api=('videobuilder.linear',), demo=lambda: None)
        return Capability(**{**base, **kw})

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
    return subprocess.run([sys.executable, '-m', 'videobuilder', 'capabilities', *args], cwd=ROOT,
                          capture_output=True, text=True)


class Cli(unittest.TestCase):
    def test_index(self):
        out = cli('index')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, registry.index_markdown())
        out = cli('index', '--json', '--family', 'typography')
        self.assertEqual(json.loads(out.stdout), registry.index_data('typography'))
        self.assertNotEqual(cli('index', '--family', 'nope').returncode, 0)

    def test_build_one_writes_clip_poster_and_gallery(self):
        with tempfile.TemporaryDirectory() as d:
            out = cli('gallery', '--out', d, '--only', 'dip-to-black', '--jobs', '2')
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sorted(os.listdir(d)), ['dip-to-black.jpg', 'dip-to-black.mp4', 'index.html'])
            page = Path(d, 'index.html').read_text()
            self.assertIn('src="dip-to-black.mp4"', page)
            self.assertIn('poster="dip-to-black.jpg"', page)
            self.assertIn('prefers-color-scheme: dark', page)
            self.assertNotIn('bounce-ease-out', page)
            self.assertNotEqual(cli('gallery', '--out', d, '--only', 'no-such-id').returncode, 0)

    def test_gallery_escapes_and_groups(self):
        from videobuilder.capabilities.gallery import gallery_html
        page = gallery_html(registry.catalog())
        self.assertLess(page.index('id="family-principles"'), page.index('id="family-transitions"'))
        # Self-contained: the only links out are the Source credits.
        self.assertNotIn('http', re.sub(r'<span class="source">.*?</span>', '', page))


_COLD_IDS = '''
import json, sys, time
t0 = time.process_time()
import videobuilder.text as text
families = []
lookup = text._warn_missing_family
def spy(family):
    families.append(family)
    return lookup(family)
text._warn_missing_family = spy
from videobuilder.capabilities import registry
n = len(registry.ids())
components = sys.modules.get('videobuilder.compendium.components')
print(json.dumps({'ids': n, 'seconds': time.process_time() - t0, 'families': families,
                  'catalog': 'videobuilder.compendium.catalog' in sys.modules,
                  'components_catalog': components is not None and 'CATALOG' in vars(components)}))
'''


class ColdIds(unittest.TestCase):
    """Listing capabilities imports every capability module, so a module that
    does real work at import (lays out text, builds a mesh, loads the
    compendium's components) slows every listing: work a module needs goes
    in the draw or demo that uses it, cached (see `functools.lru_cache`)."""

    # CPU seconds, not wall time, so a loaded box doesn't flake it: measured
    # at 1.2-1.5 s with no bytecode cache on a busy 16-core box (0.5 s with
    # one), so this is about 3x. The text and compendium checks catch the
    # known costs; the budget, whatever else a module starts doing at import.
    BUDGET = 4.5

    def test_ids_in_a_fresh_interpreter_does_no_work_at_import(self):
        proc = subprocess.run([sys.executable, '-c', _COLD_IDS], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertGreater(out['ids'], 0)
        self.assertEqual(out['families'], [], 'a capability module laid out text at import')
        self.assertFalse(out['catalog'], 'a capability module imported the compendium catalog')
        self.assertFalse(out['components_catalog'], "a capability module built the compendium's components")
        self.assertLess(out['seconds'], self.BUDGET)


class OneCapabilityAlone(unittest.TestCase):
    def test_documented_command_runs_one_capability(self):
        proc = subprocess.run([sys.executable, '-m', 'unittest', '-v',
                               'tests.test_capabilities_registry.EachCapability.test_bounce_ease_out'],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Ran 1 test', proc.stderr)


if __name__ == '__main__':
    unittest.main()

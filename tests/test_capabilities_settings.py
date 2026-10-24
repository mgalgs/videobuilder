"""videobuilder.capabilities.settings: Choice/Number/Option, `check`,
`validate` and `as_json` -- and that narration (the hand-written catalog
entry and the registry's voiceover) share one declaration."""
import unittest

from videobuilder.capabilities import registry
from videobuilder.capabilities.schema import Capability
from videobuilder.capabilities.settings import Choice, Number, Option, as_json, check, non_default, validate


def choice(id='voice', default='a', extra_options=()):
    options = (Option('A', 'a'), Option('B', 'b', preview='/sample/b')) + extra_options
    return Choice(id, id.title(), options=options, default=default)


def number(id='speed', lo=0.5, hi=2.0, step=0.1, default=1.0):
    return Number(id, id.title(), min=lo, max=hi, step=step, default=default)


class OptionChoiceNumber(unittest.TestCase):
    def test_option_needs_a_label_and_value(self):
        with self.assertRaises(ValueError):
            Option('', 'a')
        with self.assertRaises(ValueError):
            Option('A', '')

    def test_choice_needs_at_least_one_option(self):
        with self.assertRaises(ValueError):
            Choice('voice', 'Voice', options=(), default='a')

    def test_choice_default_must_be_one_of_its_options(self):
        with self.assertRaises(ValueError):
            Choice('voice', 'Voice', options=(Option('A', 'a'),), default='nope')

    def test_choice_options_must_be_option_instances(self):
        with self.assertRaises(ValueError):
            Choice('voice', 'Voice', options=({'label': 'A', 'value': 'a'},), default='a')

    def test_choice_clamp_keeps_a_known_value_and_falls_back_to_default(self):
        c = choice()
        self.assertEqual(c.clamp('b'), 'b')
        self.assertEqual(c.clamp('nope'), 'a')

    def test_choice_clamp_falls_back_to_default_for_an_unhashable_value(self):
        c = choice()
        self.assertEqual(c.clamp(['b']), 'a')
        self.assertEqual(c.clamp({}), 'a')

    def test_number_min_must_be_less_than_max(self):
        with self.assertRaises(ValueError):
            Number('speed', 'Speed', min=2.0, max=2.0, step=0.1, default=1.0)

    def test_number_step_must_be_positive(self):
        with self.assertRaises(ValueError):
            Number('speed', 'Speed', min=0.5, max=2.0, step=0, default=1.0)

    def test_number_default_must_be_in_range(self):
        with self.assertRaises(ValueError):
            Number('speed', 'Speed', min=0.5, max=2.0, step=0.1, default=3.0)

    def test_number_clamp_bounds_and_falls_back_to_default_for_junk(self):
        n = number()
        self.assertEqual(n.clamp(0.1), 0.5)
        self.assertEqual(n.clamp(5), 2.0)
        self.assertEqual(n.clamp(1.3), 1.3)
        self.assertEqual(n.clamp('not a number'), 1.0)
        self.assertEqual(n.clamp(None), 1.0)


class Check(unittest.TestCase):
    def test_accepts_choices_and_numbers(self):
        self.assertEqual(check('x', (choice(), number())), (choice(), number()))

    def test_rejects_a_non_setting_entry(self):
        with self.assertRaisesRegex(ValueError, 'x: settings entries must be a Choice or Number'):
            check('x', ({'id': 'voice'},))

    def test_rejects_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, 'x: settings has duplicate ids'):
            check('x', (choice(id='voice'), choice(id='voice')))


class Validate(unittest.TestCase):
    SETTINGS = (choice(), number())

    def test_missing_keys_get_defaults(self):
        self.assertEqual(validate(self.SETTINGS, {}), {'voice': 'a', 'speed': 1.0})

    def test_unknown_keys_are_dropped(self):
        got = validate(self.SETTINGS, {'voice': 'b', 'speed': 1.2, 'nonsense': 'x'})
        self.assertEqual(got, {'voice': 'b', 'speed': 1.2})

    def test_out_of_range_numbers_are_clamped(self):
        self.assertEqual(validate(self.SETTINGS, {'speed': 99}), {'voice': 'a', 'speed': 2.0})

    def test_unknown_choice_value_falls_back_to_default(self):
        self.assertEqual(validate(self.SETTINGS, {'voice': 'nope'}), {'voice': 'a', 'speed': 1.0})

    def test_an_unhashable_choice_value_falls_back_to_default(self):
        self.assertEqual(validate(self.SETTINGS, {'voice': ['b']}), {'voice': 'a', 'speed': 1.0})
        self.assertEqual(validate(self.SETTINGS, {'voice': {}}), {'voice': 'a', 'speed': 1.0})

    def test_a_non_dict_values_is_treated_as_empty(self):
        self.assertEqual(validate(self.SETTINGS, None), {'voice': 'a', 'speed': 1.0})
        self.assertEqual(validate(self.SETTINGS, 'nonsense'), {'voice': 'a', 'speed': 1.0})


class NonDefault(unittest.TestCase):
    SETTINGS = (choice(), number())

    def test_a_changed_value_is_kept(self):
        self.assertEqual(non_default(self.SETTINGS, {'voice': 'b'}), {'voice': 'b'})

    def test_a_value_equal_to_the_default_is_dropped(self):
        self.assertEqual(non_default(self.SETTINGS, {'voice': 'a', 'speed': 1.0}), {})

    def test_an_empty_or_missing_values_is_empty(self):
        self.assertEqual(non_default(self.SETTINGS, {}), {})
        self.assertEqual(non_default(self.SETTINGS, None), {})

    def test_an_out_of_range_number_is_clamped_then_compared_to_default(self):
        self.assertEqual(non_default(self.SETTINGS, {'speed': 99}), {'speed': 2.0})

    def test_an_unknown_choice_value_falls_back_to_default_and_is_dropped(self):
        self.assertEqual(non_default(self.SETTINGS, {'voice': 'nope'}), {})


class AsJson(unittest.TestCase):
    def test_choice_and_number_shapes(self):
        data = as_json((choice(), number()))
        self.assertEqual(data[0], {'type': 'choice', 'id': 'voice', 'label': 'Voice', 'default': 'a',
                                   'options': [{'label': 'A', 'value': 'a'},
                                              {'label': 'B', 'value': 'b', 'preview': '/sample/b'}]})
        self.assertEqual(data[1], {'type': 'number', 'id': 'speed', 'label': 'Speed', 'min': 0.5, 'max': 2.0,
                                   'step': 0.1, 'default': 1.0})

    def test_round_trips_through_json(self):
        import json
        json.dumps(as_json((choice(), number())))


class CapabilitySettings(unittest.TestCase):
    def _capability(self, **kw):
        return Capability(id='x', name='X', family='sound', group='g', definition='A thing that does X.',
                          phrasings=('do x', 'make x happen'), api=('videobuilder.speech.load',),
                          demo=lambda: None, **kw)

    def test_defaults_to_no_settings(self):
        self.assertEqual(self._capability().settings, ())

    def test_accepts_choices_and_numbers(self):
        cap = self._capability(settings=(choice(), number()))
        self.assertEqual(cap.settings, (choice(), number()))

    def test_rejects_duplicate_setting_ids(self):
        with self.assertRaisesRegex(ValueError, 'x: settings has duplicate ids'):
            self._capability(settings=(choice(id='voice'), choice(id='voice')))


class NarrationSettingsAreShared(unittest.TestCase):
    def test_the_catalog_entry_and_the_registry_capability_agree(self):
        from videobuilder import capabilities
        entry = capabilities.get('narration')
        registered = registry.get('voiceover')
        self.assertEqual(entry['settings'], registered.settings)
        ids = [s.id for s in registered.settings]
        self.assertEqual(ids, ['voice', 'speed'])

    def test_voice_is_a_choice_and_speed_a_number_in_says_own_range(self):
        registered = registry.get('voiceover')
        voice, speed = registered.settings
        self.assertIsInstance(voice, Choice)
        self.assertIsInstance(speed, Number)
        self.assertTrue(voice.options)
        self.assertEqual((speed.min, speed.max, speed.default), (0.5, 2.0, 1.0))


if __name__ == '__main__':
    unittest.main()

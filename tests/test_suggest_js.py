"""suggest.js's pick() (a suggestion becoming a chip, run as the real code),
against node. Every pick -- a look, a type style, a capability, a font, a
sound effect or a music track -- adds a chip and leaves the note's own text
untouched (see suggest-notes.md's "Rewrites" design call, which this
replaced: no insertText, no replaced span, no flash)."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / 'videobuilder'


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class HashtagCapIds(unittest.TestCase):
    """hashtagCapIds: the #id -> chip parser (see suggest-notes.md's "Rewrites"
    design call, and the chips call that replaced rewriting a capability pick
    into the note)."""

    def run_js(self, text, caps):
        js = (PKG / 'suggest.js').read_text()
        hashtag_re = re.search(r'\nconst HASHTAG_RE = .*?;', js).group(0)
        fn = re.search(r'\nfunction hashtagCapIds\(text, caps\) \{.*?\n\}', js, re.S).group(0)
        script = hashtag_re + fn + f"""
console.log(JSON.stringify(hashtagCapIds({json.dumps(text)}, {json.dumps(caps)})));
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_real_id_typed_as_a_hashtag_is_found(self):
        self.assertEqual(self.run_js('try #map-route-draw on the intro', {'map-route-draw': 1}),
                         ['map-route-draw'])

    def test_matching_is_case_insensitive_but_the_id_comes_back_lowercase(self):
        self.assertEqual(self.run_js('#Map-Route-Draw', {'map-route-draw': 1}), ['map-route-draw'])

    def test_an_unknown_hashtag_is_ordinary_text_no_chip_no_error(self):
        self.assertEqual(self.run_js('#notacap and #also-not-one', {'map-route-draw': 1}), [])

    def test_repeats_are_deduplicated(self):
        self.assertEqual(self.run_js('#a #b #a', {'a': 1, 'b': 1}), ['a', 'b'])

    def test_a_hashtag_cannot_start_with_a_digit(self):
        self.assertEqual(self.run_js('chapter #1', {'1': 1}), [])

    def test_no_hashtags_in_the_text_is_an_empty_list(self):
        self.assertEqual(self.run_js('just an ordinary note', {'a': 1}), [])


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class PickNeverTouchesTheNote(unittest.TestCase):
    """pick(): every family -- a capability (CAP_FAMILIES) or a font/sfx/music
    pick (ASSET_FAMILIES) -- adds a chip and leaves the textarea untouched.
    Neither branch references `ta` at all (checked directly on the extracted
    source, not just by example), which is what makes this true for every
    case, not just the ones exercised here."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        cap_families = re.search(r'\nconst CAP_FAMILIES = .*?;', js, re.S).group(0)
        asset_families = re.search(r'\nconst ASSET_FAMILIES = .*?;', js, re.S).group(0)
        key_of = re.search(r'\nconst keyOf = .*?;', js).group(0)
        pick = re.search(r'\nfunction pick\(i\) \{.*?\n\}', js, re.S).group(0)
        self.pick_source = pick
        script = cap_families + asset_families + key_of + pick + prelude + calls
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_pick_never_mentions_the_textarea_or_any_text_insertion(self):
        js = (PKG / 'suggest.js').read_text()
        pick = re.search(r'\nfunction pick\(i\) \{.*?\n\}', js, re.S).group(0)
        for needle in ('insertText', 'execCommand', 'ta.value', 'setRangeText'):
            self.assertNotIn(needle, pick)

    def test_a_capability_pick_adds_a_chip_and_leaves_the_note_untouched(self):
        prelude = """
let pickedCapIds = [];
let pickedAssetIds = {fonts: [], sfx: [], music: []};
let renderCapChipsCalls = 0;
function renderCapChips() { renderCapChipsCalls++ }
let shown = [{family: 'looks', id: 'look-melt'}, {family: 'fonts', id: 'cantarell'}];
let renderCalls = 0;
function render() { renderCalls++ }
const ta = {value: 'make it look like a dream'};
"""
        calls = """
pick({family: 'looks', id: 'look-melt'});
console.log(JSON.stringify({value: ta.value, pickedCapIds, renderCapChipsCalls, renderCalls,
  shownFamilies: shown.map(i => i.family)}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['value'], 'make it look like a dream')
        self.assertEqual(out['pickedCapIds'], ['look-melt'])
        self.assertEqual(out['renderCapChipsCalls'], 1)
        self.assertEqual(out['renderCalls'], 1)
        self.assertEqual(out['shownFamilies'], ['fonts'])

    def test_picking_the_same_capability_twice_does_not_duplicate_the_chip(self):
        prelude = """
let pickedCapIds = ['look-melt'];
let pickedAssetIds = {fonts: [], sfx: [], music: []};
function renderCapChips() {}
let shown = [];
function render() {}
const ta = {value: 'a note'};
"""
        calls = """
pick({family: 'looks', id: 'look-melt'});
console.log(JSON.stringify({pickedCapIds}));
"""
        self.assertEqual(self.run_js(prelude, calls)['pickedCapIds'], ['look-melt'])

    def test_a_font_pick_adds_a_chip_and_leaves_the_note_untouched(self):
        prelude = """
let pickedCapIds = [];
let pickedAssetIds = {fonts: [], sfx: [], music: []};
let renderCapChipsCalls = 0;
function renderCapChips() { renderCapChipsCalls++ }
let shown = [{family: 'fonts', id: 'cantarell'}, {family: 'looks', id: 'look-melt'}];
function render() {}
const ta = {value: 'Use a friendlier font for the title'};
"""
        calls = """
pick({family: 'fonts', id: 'cantarell'});
console.log(JSON.stringify({value: ta.value, pickedAssetIds, renderCapChipsCalls,
  shownFamilies: shown.map(i => i.family)}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['value'], 'Use a friendlier font for the title')
        self.assertEqual(out['pickedAssetIds'], {'fonts': ['cantarell'], 'sfx': [], 'music': []})
        self.assertEqual(out['renderCapChipsCalls'], 1)
        self.assertEqual(out['shownFamilies'], ['looks'])

    def test_an_sfx_and_a_music_pick_are_tracked_in_their_own_family(self):
        prelude = """
let pickedCapIds = [];
let pickedAssetIds = {fonts: [], sfx: [], music: []};
function renderCapChips() {}
let shown = [];
function render() {}
const ta = {value: 'Make each price appear in turn, with a launch song behind it.'};
"""
        calls = """
pick({family: 'sfx', id: 'fit/tick/domino'});
pick({family: 'music', id: 'bright-steps'});
console.log(JSON.stringify({value: ta.value, pickedAssetIds}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['value'], 'Make each price appear in turn, with a launch song behind it.')
        self.assertEqual(out['pickedAssetIds'], {'fonts': [], 'sfx': ['fit/tick/domino'], 'music': ['bright-steps']})

    def test_picking_the_same_asset_twice_does_not_duplicate_the_chip(self):
        prelude = """
let pickedCapIds = [];
let pickedAssetIds = {fonts: ['cantarell'], sfx: [], music: []};
function renderCapChips() {}
let shown = [];
function render() {}
const ta = {value: 'a note'};
"""
        calls = """
pick({family: 'fonts', id: 'cantarell'});
console.log(JSON.stringify({pickedAssetIds}));
"""
        self.assertEqual(self.run_js(prelude, calls)['pickedAssetIds'], {'fonts': ['cantarell'], 'sfx': [], 'music': []})


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class CapabilitySettingsCards(unittest.TestCase):
    """renderCapChips: a chip whose capability declares `settings` (see
    capabilities/settings.py's as_json, which is what CAPS[id].settings holds
    here) gets its own settings card, stacked below the chip row in chip
    order; removing the chip drops its card and any values it picked."""

    NARRATION_SETTINGS = [
        {'type': 'choice', 'id': 'voice', 'label': 'Voice', 'default': 'bf_isabella',
         'options': [{'label': 'Isabella', 'value': 'bf_isabella'}, {'label': 'Heart', 'value': 'af_heart'}]},
        {'type': 'number', 'id': 'speed', 'label': 'Speed', 'default': 1.0, 'min': 0.5, 'max': 2.0, 'step': 0.1},
    ]

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        hashtag_re = re.search(r'\nconst HASHTAG_RE = .*?;', js).group(0)
        hashtag_fn = re.search(r'\nfunction hashtagCapIds\(text, caps\) \{.*?\n\}', js, re.S).group(0)
        # Not `.*?;`: esc's own replacement map holds entities like '&amp;' that carry a
        # literal semicolon, which would end the match early.
        esc = re.search(r'\nconst esc = [^\n]*', js).group(0)
        svg = re.search(r'\nconst svg = [^\n]*', js).group(0)
        icons = re.search(r'\nconst I = \{.*?\n\};', js, re.S).group(0)
        cap_chip_ids = re.search(r'\nfunction capChipIds\(\) \{.*?\n\}', js, re.S).group(0)
        diff = re.search(r'\nfunction settingsValuesDiff\(settings, values\) \{.*?\n\}', js, re.S).group(0)
        render_cap_chips = re.search(r'\nfunction renderCapChips\(\) \{.*?\n\}', js, re.S).group(0)
        asset_families = re.search(r'\nconst ASSET_FAMILIES = .*?;', js, re.S).group(0)
        # Not `.*?;`: el's own body has a semicolon after each of its own statements.
        el = re.search(r'\nconst el = [^\n]*', js).group(0)
        dom = """
function makeEl() {
  return {
    className: '', innerHTML: '', children: [], attrs: {},
    append(...xs) { this.children.push(...xs) },
    replaceChildren(...xs) { this.children = xs },
    setAttribute(k, v) { this.attrs[k] = v },
    getAttribute(k) { return this.attrs[k] },
  };
}
const document = {createElement: () => makeEl()};
let capCardsKey = null;
let pickedAssetIds = {fonts: [], sfx: [], music: []};
const window = {SettingsCard: {calls: [], render(container, settings, values, onChange) {
  window.SettingsCard.calls.push({container, settings, values});
  window.SettingsCard.lastOnChange = onChange;
}}};
"""
        script = (dom + hashtag_re + hashtag_fn + esc + svg + icons + el + asset_families + cap_chip_ids + diff +
                  render_cap_chips + prelude + calls)
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_chip_with_settings_mounts_a_card_below_the_chip_row(self):
        prelude = f"""
const CAPS = {{narration: {{id: 'narration', family: 'capabilities', title: 'Narration',
  settings: {json.dumps(self.NARRATION_SETTINGS)}}}}};
let pickedCapIds = ['narration'];
let capValues = {{}};
const ta = {{value: ''}};
const capChips = makeEl(), capCards = makeEl();
"""
        calls = """
renderCapChips();
console.log(JSON.stringify({chipCount: capChips.children.length, cardCount: capCards.children.length,
  renderCalls: window.SettingsCard.calls.length}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['chipCount'], 1)
        self.assertEqual(out['cardCount'], 1)
        self.assertEqual(out['renderCalls'], 1)

    def test_a_chip_without_settings_mounts_no_card(self):
        prelude = """
const CAPS = {'look-melt': {id: 'look-melt', family: 'looks', title: 'Surrealist melt', settings: null}};
let pickedCapIds = ['look-melt'];
let capValues = {};
const ta = {value: ''};
const capChips = makeEl(), capCards = makeEl();
"""
        calls = """
renderCapChips();
console.log(JSON.stringify({chipCount: capChips.children.length, cardCount: capCards.children.length,
  renderCalls: window.SettingsCard.calls.length}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['chipCount'], 1)
        self.assertEqual(out['cardCount'], 0)
        self.assertEqual(out['renderCalls'], 0)

    def test_picking_a_value_in_the_card_keeps_only_the_non_default_one(self):
        prelude = f"""
const CAPS = {{narration: {{id: 'narration', family: 'capabilities', title: 'Narration',
  settings: {json.dumps(self.NARRATION_SETTINGS)}}}}};
let pickedCapIds = ['narration'];
let capValues = {{}};
const ta = {{value: ''}};
const capChips = makeEl(), capCards = makeEl();
"""
        calls = """
renderCapChips();
window.SettingsCard.lastOnChange({voice: 'af_heart', speed: 1.0});
console.log(JSON.stringify({capValues}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['capValues'], {'narration': {'voice': 'af_heart'}})

    def test_removing_the_chip_drops_its_card_and_its_values(self):
        prelude = f"""
const CAPS = {{narration: {{id: 'narration', family: 'capabilities', title: 'Narration',
  settings: {json.dumps(self.NARRATION_SETTINGS)}}}}};
let pickedCapIds = ['narration'];
let capValues = {{narration: {{voice: 'af_heart'}}}};
const ta = {{value: ''}};
const capChips = makeEl(), capCards = makeEl();
"""
        calls = """
renderCapChips();
const chipSpan = capChips.children[0];
const removeButton = chipSpan.children[chipSpan.children.length - 1];
removeButton.onclick();
console.log(JSON.stringify({pickedCapIds, capValues, cardCount: capCards.children.length}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['pickedCapIds'], [])
        self.assertEqual(out['capValues'], {})
        self.assertEqual(out['cardCount'], 0)

    def test_typing_does_not_rebuild_an_unchanged_card(self):
        # A rebuild on every keystroke would cut off a voice sample mid-play.
        prelude = f"""
const CAPS = {{narration: {{id: 'narration', family: 'capabilities', title: 'Narration',
  settings: {json.dumps(self.NARRATION_SETTINGS)}}}}};
let pickedCapIds = ['narration'];
let capValues = {{}};
const ta = {{value: ''}};
const capChips = makeEl(), capCards = makeEl();
"""
        calls = """
renderCapChips();
const card = capCards.children[0];
ta.value = 'more words';
renderCapChips();
console.log(JSON.stringify({renderCalls: window.SettingsCard.calls.length, same: capCards.children[0] === card}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['renderCalls'], 1)
        self.assertTrue(out['same'])


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class AssetChips(unittest.TestCase):
    """renderCapChips: a picked font/sfx/music chip, in the same row as a
    capability chip, named by nameOf and marked with an icon plus a plain
    kind label ("Font"/"Sound"/"Music" -- never colour alone), a play button
    for a sound or a music track (not a font), and an x that drops it."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        hashtag_re = re.search(r'\nconst HASHTAG_RE = .*?;', js).group(0)
        hashtag_fn = re.search(r'\nfunction hashtagCapIds\(text, caps\) \{.*?\n\}', js, re.S).group(0)
        cap_chip_ids = re.search(r'\nfunction capChipIds\(\) \{.*?\n\}', js, re.S).group(0)
        render_cap_chips = re.search(r'\nfunction renderCapChips\(\) \{.*?\n\}', js, re.S).group(0)
        asset_families = re.search(r'\nconst ASSET_FAMILIES = .*?;', js, re.S).group(0)
        asset_label = re.search(r'\nconst ASSET_LABEL = \{.*?\};', js, re.S).group(0)
        key_of = re.search(r'\nconst keyOf = .*?;', js).group(0)
        name_of = re.search(r'\nconst nameOf = .*?\n.*?;', js).group(0)
        # Not `.*?;`: esc's own replacement map holds entities that carry a literal semicolon.
        esc = re.search(r'\nconst esc = [^\n]*', js).group(0)
        svg = re.search(r'\nconst svg = [^\n]*', js).group(0)
        icons = re.search(r'\nconst I = \{.*?\n\};', js, re.S).group(0)
        el = re.search(r'\nconst el = [^\n]*', js).group(0)
        dom = """
function makeEl() {
  return {
    className: '', innerHTML: '', children: [], attrs: {},
    append(...xs) { this.children.push(...xs) },
    replaceChildren(...xs) { this.children = xs },
    setAttribute(k, v) { this.attrs[k] = v },
    getAttribute(k) { return this.attrs[k] },
  };
}
const document = {createElement: () => makeEl()};
let CAPS = {};
let pickedCapIds = [];
let capCardsKey = null, capCards = null;
let playCalls = [];
function play(i) { playCalls.push(i) }
let playing = null;
let stopAllCalls = 0;
function stopAll() { stopAllCalls++; playing = null }
"""
        script = (dom + hashtag_re + hashtag_fn + key_of + name_of + esc + svg + icons + el + asset_families +
                  asset_label + cap_chip_ids + render_cap_chips + prelude + calls)
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_font_chip_has_no_play_button(self):
        prelude = """
const BY = {'fonts:cantarell': {id: 'cantarell', family: 'Cantarell'}};
let pickedAssetIds = {fonts: ['cantarell'], sfx: [], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
const chip = capChips.children[0];
console.log(JSON.stringify({chipCount: capChips.children.length, html: chip.children.map(c => c.innerHTML),
  kinds: chip.children.map(c => c.className)}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['chipCount'], 1)
        self.assertIn('sg-assetchip-kind', out['kinds'])
        self.assertNotIn('sg-assetchip-play', out['kinds'])
        self.assertTrue(any('Cantarell' in h for h in out['html']))
        self.assertTrue(any('Font' in h for h in out['html']))

    def test_a_sound_chip_has_a_play_button_that_calls_play(self):
        prelude = """
const BY = {'sfx:fit/tick/domino': {id: 'fit/tick/domino', role: 'tick'}};
let pickedAssetIds = {fonts: [], sfx: ['fit/tick/domino'], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
const chip = capChips.children[0];
const playButton = chip.children.find(c => c.className === 'sg-assetchip-play');
playButton.onclick();
console.log(JSON.stringify({kinds: chip.children.map(c => c.className), playCalls}));
"""
        out = self.run_js(prelude, calls)
        self.assertIn('sg-assetchip-play', out['kinds'])
        self.assertEqual(out['playCalls'], [{'family': 'sfx', 'id': 'fit/tick/domino'}])

    def test_a_music_chip_also_has_a_play_button(self):
        prelude = """
const BY = {'music:bright-steps': {id: 'bright-steps', title: 'Bright Steps'}};
let pickedAssetIds = {fonts: [], sfx: [], music: ['bright-steps']};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
const chip = capChips.children[0];
console.log(JSON.stringify({kinds: chip.children.map(c => c.className),
  html: chip.children.map(c => c.innerHTML)}));
"""
        out = self.run_js(prelude, calls)
        self.assertIn('sg-assetchip-play', out['kinds'])
        self.assertTrue(any('Bright Steps' in h for h in out['html']))
        self.assertTrue(any('Music' in h for h in out['html']))

    def test_removing_the_chip_drops_it_from_pickedassetids(self):
        prelude = """
const BY = {'fonts:cantarell': {id: 'cantarell', family: 'Cantarell'}};
let pickedAssetIds = {fonts: ['cantarell'], sfx: [], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
const chip = capChips.children[0];
const removeButton = chip.children[chip.children.length - 1];
removeButton.onclick();
console.log(JSON.stringify({pickedAssetIds, chipCountAfter: capChips.children.length}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['pickedAssetIds'], {'fonts': [], 'sfx': [], 'music': []})
        self.assertEqual(out['chipCountAfter'], 0)

    def test_removing_a_playing_chip_stops_the_audio_first(self):
        prelude = """
const BY = {'sfx:fit/tick/domino': {id: 'fit/tick/domino', role: 'tick'}};
let pickedAssetIds = {fonts: [], sfx: ['fit/tick/domino'], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
playing = {key: 'sfx:fit/tick/domino'};
const chip = capChips.children[0];
const removeButton = chip.children[chip.children.length - 1];
removeButton.onclick();
console.log(JSON.stringify({stopAllCalls, playing}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['stopAllCalls'], 1)
        self.assertIsNone(out['playing'])

    def test_removing_a_different_chip_does_not_stop_the_audio(self):
        prelude = """
const BY = {'sfx:fit/tick/domino': {id: 'fit/tick/domino', role: 'tick'},
            'fonts:cantarell': {id: 'cantarell', family: 'Cantarell'}};
let pickedAssetIds = {fonts: ['cantarell'], sfx: ['fit/tick/domino'], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
playing = {key: 'sfx:fit/tick/domino'};
const fontChip = capChips.children.find(c => c.children.some(x => x.innerHTML.includes('Cantarell')));
const removeButton = fontChip.children[fontChip.children.length - 1];
removeButton.onclick();
console.log(JSON.stringify({stopAllCalls, playing}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['stopAllCalls'], 0)
        self.assertEqual(out['playing'], {'key': 'sfx:fit/tick/domino'})

    def test_a_chip_playing_audio_survives_an_unrelated_rerender(self):
        # A keystroke (or picking/removing an unrelated chip) calls renderCapChips again;
        # a chip mid-playback must keep the exact button node play() is tracking, or its
        # stop icon reverts to a play icon and the next click just stops the track.
        prelude = """
const BY = {'sfx:fit/tick/domino': {id: 'fit/tick/domino', role: 'tick'}};
let pickedAssetIds = {fonts: [], sfx: ['fit/tick/domino'], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
const chip1 = capChips.children[0];
const playButton1 = chip1.children.find(c => c.className === 'sg-assetchip-play');
playButton1.innerHTML = 'stop-icon-marker';
renderCapChips();
const chip2 = capChips.children[0];
const playButton2 = chip2.children.find(c => c.className === 'sg-assetchip-play');
console.log(JSON.stringify({sameNode: chip1 === chip2, samePlayButton: playButton1 === playButton2,
  markerSurvived: playButton2.innerHTML === 'stop-icon-marker'}));
"""
        out = self.run_js(prelude, calls)
        self.assertTrue(out['sameNode'])
        self.assertTrue(out['samePlayButton'])
        self.assertTrue(out['markerSurvived'])

    def test_a_capability_chip_and_an_asset_chip_share_the_same_row(self):
        prelude = """
CAPS = {'look-melt': {id: 'look-melt', family: 'looks', title: 'Surrealist melt', settings: null}};
const BY = {'fonts:cantarell': {id: 'cantarell', family: 'Cantarell'}};
pickedCapIds = ['look-melt'];
let pickedAssetIds = {fonts: ['cantarell'], sfx: [], music: []};
const ta = {value: ''};
const capChips = makeEl();
"""
        calls = """
renderCapChips();
console.log(JSON.stringify({chipCount: capChips.children.length}));
"""
        self.assertEqual(self.run_js(prelude, calls)['chipCount'], 2)


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class CapabilityEntriesForTheNote(unittest.TestCase):
    """capChipEntries (wired as noteCapabilityIds, see director.js's addPending/
    sendNow/batchBody) and the restorePickedCapIds assignment inside start()
    (see director.js's editPending): the {id, settings} shape a note actually
    carries, and how a pending note's own chips and values come back."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        hashtag_re = re.search(r'\nconst HASHTAG_RE = .*?;', js).group(0)
        hashtag_fn = re.search(r'\nfunction hashtagCapIds\(text, caps\) \{.*?\n\}', js, re.S).group(0)
        cap_chip_ids = re.search(r'\nfunction capChipIds\(\) \{.*?\n\}', js, re.S).group(0)
        cap_chip_entries = re.search(r'\nfunction capChipEntries\(\) \{.*?\n\}', js, re.S).group(0)
        restore = re.search(r'\n  restorePickedCapIds = entries => \{.*?\n  \};', js, re.S).group(0)
        script = f"""
const CAPS = {{}};
let pickedCapIds = [];
let capValues = {{}};
let restorePickedCapIds;
{hashtag_re}{hashtag_fn}{cap_chip_ids}{cap_chip_entries}
{restore}
{prelude}
{calls}
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_picked_ids_entry_carries_its_non_default_settings(self):
        prelude = "const ta = {value: ''}; pickedCapIds = ['narration']; capValues = {narration: {voice: 'af_heart'}};"
        calls = "console.log(JSON.stringify(capChipEntries()));"
        self.assertEqual(self.run_js(prelude, calls), [{'id': 'narration', 'settings': {'voice': 'af_heart'}}])

    def test_a_chip_with_no_values_sends_an_empty_settings_object(self):
        prelude = "const ta = {value: ''}; pickedCapIds = ['look-melt']; capValues = {};"
        calls = "console.log(JSON.stringify(capChipEntries()));"
        self.assertEqual(self.run_js(prelude, calls), [{'id': 'look-melt', 'settings': {}}])

    def test_restore_recovers_ids_and_values_from_entries(self):
        calls = """
restorePickedCapIds([{id: 'narration', settings: {voice: 'af_heart'}}, 'look-melt']);
console.log(JSON.stringify({pickedCapIds, capValues}));
"""
        out = self.run_js('', calls)
        self.assertEqual(out['pickedCapIds'], ['narration', 'look-melt'])
        self.assertEqual(out['capValues'], {'narration': {'voice': 'af_heart'}})

    def test_restore_with_nothing_clears_picked_ids_and_values(self):
        prelude = "pickedCapIds = ['narration']; capValues = {narration: {voice: 'af_heart'}};"
        calls = "restorePickedCapIds([]); console.log(JSON.stringify({pickedCapIds, capValues}));"
        out = self.run_js(prelude, calls)
        self.assertEqual(out['pickedCapIds'], [])
        self.assertEqual(out['capValues'], {})


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class AssetEntriesForTheNote(unittest.TestCase):
    """assetPickEntries (wired as noteAssetIds, see director.js's addPending/
    sendNow/batchBody) and the restorePickedAssetIds assignment inside start()
    (see director.js's editPending): the {fonts, sfx, music} shape a note
    actually carries, and how a pending note's own chips come back."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        asset_pick_entries = re.search(r'\nfunction assetPickEntries\(\) \{.*?\n\}', js, re.S).group(0)
        restore = re.search(r'\n  restorePickedAssetIds = assets => \{.*?\n  \};', js, re.S).group(0)
        script = f"""
let pickedAssetIds = {{fonts: [], sfx: [], music: []}};
let restorePickedAssetIds;
{asset_pick_entries}
{restore}
{prelude}
{calls}
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_entries_reflect_each_familys_picked_ids(self):
        prelude = "pickedAssetIds = {fonts: ['cantarell'], sfx: ['fit/tick/domino'], music: []};"
        calls = "console.log(JSON.stringify(assetPickEntries()));"
        self.assertEqual(self.run_js(prelude, calls),
                         {'fonts': ['cantarell'], 'sfx': ['fit/tick/domino'], 'music': []})

    def test_restore_recovers_ids_per_family(self):
        calls = """
restorePickedAssetIds({fonts: ['cantarell'], sfx: [], music: ['bright-steps']});
console.log(JSON.stringify(pickedAssetIds));
"""
        self.assertEqual(self.run_js('', calls), {'fonts': ['cantarell'], 'sfx': [], 'music': ['bright-steps']})

    def test_restore_dedups_repeated_ids_within_a_family(self):
        calls = """
restorePickedAssetIds({fonts: ['cantarell', 'cantarell'], sfx: [], music: []});
console.log(JSON.stringify(pickedAssetIds));
"""
        self.assertEqual(self.run_js('', calls), {'fonts': ['cantarell'], 'sfx': [], 'music': []})

    def test_restore_with_nothing_clears_every_family(self):
        prelude = "pickedAssetIds = {fonts: ['cantarell'], sfx: ['x'], music: ['y']};"
        calls = "restorePickedAssetIds({fonts: [], sfx: [], music: []}); console.log(JSON.stringify(pickedAssetIds));"
        self.assertEqual(self.run_js(prelude, calls), {'fonts': [], 'sfx': [], 'music': []})

    def test_restore_from_a_pending_note_saved_before_these_fields_shipped(self):
        # director.js's editPending falls back to [] for a missing field before calling this.
        prelude = "pickedAssetIds = {fonts: ['cantarell'], sfx: [], music: []};"
        calls = "restorePickedAssetIds({fonts: [], sfx: [], music: []}); console.log(JSON.stringify(pickedAssetIds));"
        self.assertEqual(self.run_js(prelude, calls), {'fonts': [], 'sfx': [], 'music': []})


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class BatchBodyCapabilities(unittest.TestCase):
    """director.js's batchBody: each pending item's capabilities is now a list of
    {id, settings} (suggest.js's noteCapabilityIds), so the merge across items
    dedups by id, not by the whole object, keeping the first occurrence's
    settings."""

    def run_js(self, items):
        js = (PKG / 'director.js').read_text()
        batch_body = re.search(r'\nfunction batchBody\(items\) \{.*?\n\}', js, re.S).group(0)
        script = f"""
function timeLabel() {{ return '0:00' }}
{batch_body}
console.log(JSON.stringify(batchBody({json.dumps(items)}).capabilities));
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_single_items_capabilities_pass_through(self):
        items = [{'text': 'a', 'attachments': [], 'capabilities': [{'id': 'narration', 'settings': {'speed': 1.2}}]}]
        self.assertEqual(self.run_js(items), [{'id': 'narration', 'settings': {'speed': 1.2}}])

    def test_the_same_id_across_items_is_kept_once_first_occurrence_wins(self):
        items = [{'text': 'a', 'attachments': [], 'capabilities': [{'id': 'narration', 'settings': {'speed': 1.2}}]},
                 {'text': 'b', 'attachments': [], 'capabilities': [{'id': 'narration', 'settings': {'speed': 0.5}},
                                                                   {'id': 'look-melt', 'settings': {}}]}]
        self.assertEqual(self.run_js(items), [{'id': 'narration', 'settings': {'speed': 1.2}},
                                              {'id': 'look-melt', 'settings': {}}])

    def test_a_legacy_plain_id_string_from_a_pending_item_saved_before_this_shipped_is_kept(self):
        items = [{'text': 'a', 'attachments': [], 'capabilities': ['narration', 'look-melt']},
                 {'text': 'b', 'attachments': [], 'capabilities': [{'id': 'map-route-draw', 'settings': {}}]}]
        self.assertEqual(self.run_js(items), [{'id': 'narration'}, {'id': 'look-melt'},
                                              {'id': 'map-route-draw', 'settings': {}}])


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class BatchBodyAssets(unittest.TestCase):
    """director.js's batchBody: each pending item's fonts/sfx/music is a plain
    list of ids (suggest.js's noteAssetIds); the merge across items dedups by
    id, first occurrence wins, keeping pick order -- and an old pending item
    saved before these fields shipped (no fonts/sfx/music keys at all) still
    sends, as if it simply picked none of them."""

    def run_js(self, items):
        js = (PKG / 'director.js').read_text()
        batch_body = re.search(r'\nfunction batchBody\(items\) \{.*?\n\}', js, re.S).group(0)
        script = f"""
function timeLabel() {{ return '0:00' }}
{batch_body}
const out = batchBody({json.dumps(items)});
console.log(JSON.stringify({{fonts: out.fonts, sfx: out.sfx, music: out.music}}));
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_single_items_assets_pass_through(self):
        items = [{'text': 'a', 'attachments': [], 'fonts': ['cantarell'], 'sfx': ['fit/tick/domino'], 'music': []}]
        self.assertEqual(self.run_js(items), {'fonts': ['cantarell'], 'sfx': ['fit/tick/domino'], 'music': []})

    def test_the_same_id_across_items_is_kept_once_first_occurrence_wins(self):
        items = [{'text': 'a', 'attachments': [], 'fonts': ['cantarell'], 'sfx': [], 'music': ['bright-steps']},
                 {'text': 'b', 'attachments': [], 'fonts': ['cantarell', 'dejavu-sans'], 'sfx': [], 'music': []}]
        self.assertEqual(self.run_js(items), {'fonts': ['cantarell', 'dejavu-sans'], 'sfx': [],
                                              'music': ['bright-steps']})

    def test_an_old_pending_item_with_no_asset_fields_still_sends(self):
        items = [{'text': 'a', 'attachments': [], 'capabilities': []},
                 {'text': 'b', 'attachments': [], 'fonts': ['cantarell'], 'sfx': [], 'music': []}]
        self.assertEqual(self.run_js(items), {'fonts': ['cantarell'], 'sfx': [], 'music': []})


class PageWiring(unittest.TestCase):
    """The composer loads the suggest layer."""

    def test_editor_html_loads_suggest_css_and_js(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('<link rel="stylesheet" href="suggest.css">', html)
        self.assertIn('<script src="suggest.js" defer', html)

    def test_editor_html_loads_settings_card_css_and_js(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('<link rel="stylesheet" href="settings_card.css">', html)
        self.assertIn('<script src="settings_card.js" defer', html)

    def test_editor_composer_markup_suggest_js_hooks_into(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('id="composer"', html)
        self.assertIn('class="composer-extras"', html)
        self.assertIn('id="message"', html)

    def test_director_js_clears_suggestions_after_sending_a_note(self):
        js = (PKG / 'director.js').read_text()
        add_pending = re.search(r'async function addPending\(\) \{.*?\n\}', js, re.S).group(0)
        self.assertLess(add_pending.index("$('message').value=''"),
                        add_pending.index("dispatchEvent(new Event('input'"))


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class OnInputStopsAudio(unittest.TestCase):
    """onInput: clearing the note (an empty textarea, which is also what
    director.js leaves behind after sending a note -- see
    test_director_js_clears_suggestions_after_sending_a_note) resets every
    picked chip. A sound or music chip held the only play button for its
    track, so clearing the chips without stopping the audio would leave it
    playing with no way to stop it."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        on_input = re.search(r'\nfunction onInput\(\) \{.*?\n\}', js, re.S).group(0)
        script = prelude + on_input + calls
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_clearing_the_note_stops_any_playing_audio(self):
        prelude = """
let dismissed = true, shown = [{x: 1}], staticChips = true, sentText = 'x';
let pickedCapIds = ['a'], capValues = {a: {}};
let pickedAssetIds = {fonts: [], sfx: ['fit/tick/domino'], music: []};
let stopAllCalls = 0;
function stopAll() { stopAllCalls++ }
function render() {}
function renderCapChips() {}
function cancel() {}
let modelOn = null;
const ta = {value: ''};
"""
        calls = "onInput(); console.log(JSON.stringify({stopAllCalls, pickedAssetIds}));"
        out = self.run_js(prelude, calls)
        self.assertEqual(out['stopAllCalls'], 1)
        self.assertEqual(out['pickedAssetIds'], {'fonts': [], 'sfx': [], 'music': []})

    def test_typing_non_empty_text_does_not_stop_audio(self):
        prelude = """
let dismissed = false, shown = [], staticChips = false, sentText = null;
let pickedCapIds = [], capValues = {};
let pickedAssetIds = {fonts: [], sfx: ['fit/tick/domino'], music: []};
let stopAllCalls = 0;
function stopAll() { stopAllCalls++ }
function render() {}
function renderCapChips() {}
function cancel() {}
let modelOn = null, timer = 0;
function ask() {}
const DEBOUNCE_MS = 1;
const ta = {value: 'still writing'};
"""
        calls = "onInput(); console.log(JSON.stringify({stopAllCalls}));"
        out = self.run_js(prelude, calls)
        self.assertEqual(out['stopAllCalls'], 0)


if __name__ == '__main__':
    unittest.main()

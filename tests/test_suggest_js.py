"""suggest.js's rewrite rules (a pick's words, run as the real code), against
node: the model's own `replace.span`/`replace.text` is used when the span is
still in the note; otherwise a per-family template either grows the last
matching phrase or appends a short clause -- see suggest-notes.md's
"Rewrites" design call."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / 'videobuilder'


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class Rewrite(unittest.TestCase):
    def run_rewrite(self, by, cases):
        js = (PKG / 'suggest.js').read_text()
        key_of = re.search(r'\nconst keyOf = .*?;', js).group(0)
        template = re.search(r'\nconst TEMPLATE = \{.*?\n\};', js, re.S).group(0)
        open_end = re.search(r'\nconst OPEN_END = .*?;', js).group(0)
        name = re.search(r'\nconst NAME = \{.*?\n\};', js, re.S).group(0)
        rewrite = re.search(r'\nfunction rewrite\(text, i\) \{.*?\n\}', js, re.S).group(0)
        script = key_of + template + open_end + name + rewrite + f"""
const BY = {json.dumps(by)};
const out = [];
for (const [text, item] of {json.dumps(cases)}) {{
  out.push(rewrite(text, item));
}}
console.log(JSON.stringify(out));
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_model_replace_used_when_span_still_in_text(self):
        text = 'Make the intro look like a comic, and add a whoosh'
        item = {'family': 'looks', 'id': 'look-pop-art',
               'replace': {'span': 'look like a comic', 'text': 'look like a comic, in the Pop-art halftone look'}}
        [[a, b, t]] = self.run_rewrite({}, [[text, item]])
        self.assertEqual(text[a:b], 'look like a comic')
        self.assertEqual(t, 'look like a comic, in the Pop-art halftone look')

    def test_note_ending_on_an_open_word_is_finished_by_the_name(self):
        by = {'looks:look-melt': {'title': 'Surrealist melt'}, 'fonts:cantarell': {'family': 'Cantarell'}}
        cases = [['change the look to', {'family': 'looks', 'id': 'look-melt', 'replace': None}],
                 ['set the title in a font like ', {'family': 'fonts', 'id': 'cantarell', 'replace': None}]]
        out = self.run_rewrite(by, cases)
        self.assertEqual([text[:a] + t + text[b:] for (text, _), (a, b, t) in zip(cases, out)],
                         ['change the look to Surrealist melt', 'set the title in a font like Cantarell'])

    def test_open_ending_beats_the_models_own_replace(self):
        text = 'change the look to'
        item = {'family': 'looks', 'id': 'look-melt', 'replace': {'span': 'look', 'text': 'look (Surrealist melt)'}}
        [[a, b, t]] = self.run_rewrite({'looks:look-melt': {'title': 'Surrealist melt'}}, [[text, item]])
        self.assertEqual(text[:a] + t + text[b:], 'change the look to Surrealist melt')

    def test_look_template_names_the_look_without_splitting_the_sentence(self):
        text = 'make the look warmer'
        item = {'family': 'looks', 'id': 'look-melt', 'replace': None}
        [[a, b, t]] = self.run_rewrite({'looks:look-melt': {'title': 'Surrealist melt'}}, [[text, item]])
        self.assertEqual(text[:a] + t + text[b:], 'make the look (Surrealist melt) warmer')

    def test_font_template_adds_parens_after_the_word_font(self):
        text = 'Use a friendlier font for the title'
        item = {'family': 'fonts', 'id': 'cantarell', 'replace': None}
        by = {'fonts:cantarell': {'family': 'Cantarell'}}
        [[a, b, t]] = self.run_rewrite(by, [[text, item]])
        self.assertEqual(text[:a] + t + text[b:], 'Use a friendlier font (Cantarell) for the title')

    def test_sfx_with_no_matching_word_appends_a_clause_before_final_punctuation(self):
        text = 'Make each price appear in turn.'
        item = {'family': 'sfx', 'id': 'fit/tick/domino', 'replace': None}
        by = {'sfx:fit/tick/domino': {'id': 'fit/tick/domino', 'role': 'tick'}}
        # No sfx-shaped word (whoosh/hit/pop/tick/...) is in the text, so this falls through
        # to the append-a-clause branch, same as the design note's own example.
        [[a, b, t]] = self.run_rewrite(by, [[text, item]])
        self.assertEqual(a, b)
        self.assertEqual(text[:a] + t + text[a:], 'Make each price appear in turn, with a tick (fit/tick/domino).')

    def test_music_template_appends_clause_with_no_music_word(self):
        text = 'A 30-second launch video for our app'
        item = {'family': 'music', 'id': 'bright-steps', 'replace': None}
        by = {'music:bright-steps': {'title': 'Bright Steps', 'source': 'Example Library'}}
        [[a, b, t]] = self.run_rewrite(by, [[text, item]])
        self.assertEqual(text + t, 'A 30-second launch video for our app, with "Bright Steps" '
                                   '(Example Library) as the music')


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
class CapabilityPickNeverRewrites(unittest.TestCase):
    """pick(): a capability-family suggestion (CAP_FAMILIES) adds a chip and
    leaves the textarea untouched; any other family still rewrites the note
    exactly as before (see Rewrite, above)."""

    def run_js(self, prelude, calls):
        js = (PKG / 'suggest.js').read_text()
        cap_families = re.search(r'\nconst CAP_FAMILIES = .*?;', js, re.S).group(0)
        key_of = re.search(r'\nconst keyOf = .*?;', js).group(0)
        pick = re.search(r'\nfunction pick\(i, \{user\} = \{\}\) \{.*?\n\}', js, re.S).group(0)
        script = cap_families + key_of + pick + prelude + calls
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_a_capability_pick_adds_a_chip_and_leaves_the_note_untouched(self):
        prelude = """
let pickedCapIds = [];
let renderCapChipsCalls = 0;
function renderCapChips() { renderCapChipsCalls++ }
let shown = [{family: 'looks', id: 'look-melt'}, {family: 'fonts', id: 'cantarell'}];
let renderCalls = 0;
function render() { renderCalls++ }
const ta = {value: 'make it look like a dream'};
"""
        calls = """
pick({family: 'looks', id: 'look-melt'}, {user: true});
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
function renderCapChips() {}
let shown = [];
function render() {}
const ta = {value: 'a note'};
"""
        calls = """
pick({family: 'looks', id: 'look-melt'}, {user: true});
console.log(JSON.stringify({pickedCapIds}));
"""
        self.assertEqual(self.run_js(prelude, calls)['pickedCapIds'], ['look-melt'])

    def test_a_non_capability_pick_still_rewrites_the_note(self):
        prelude = """
let pickedCapIds = [];
function renderCapChips() {}
let shown = [{family: 'fonts', id: 'cantarell'}];
function render() {}
let programmatic = false;
const ta = {
  value: 'Use a friendlier font for the title',
  focus() {}, setSelectionRange() {},
  setRangeText(text, a, b) { this.value = this.value.slice(0, a) + text + this.value.slice(b) },
  dispatchEvent() {},
};
const document = {execCommand: () => false};
function rewrite(text, i) {
  const m = / font\\b/.exec(text);
  return [m.index, m.index + m[0].length, ' font (Cantarell)'];
}
function flash() {}
"""
        calls = """
pick({family: 'fonts', id: 'cantarell'}, {user: true});
console.log(JSON.stringify({value: ta.value, pickedCapIds}));
"""
        out = self.run_js(prelude, calls)
        self.assertEqual(out['value'], 'Use a friendlier font (Cantarell) for the title')
        self.assertEqual(out['pickedCapIds'], [])


class PageWiring(unittest.TestCase):
    """The composer loads the suggest layer."""

    def test_editor_html_loads_suggest_css_and_js(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('<link rel="stylesheet" href="suggest.css">', html)
        self.assertIn('<script src="suggest.js" defer', html)

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


if __name__ == '__main__':
    unittest.main()

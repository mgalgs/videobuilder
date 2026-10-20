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


class PageWiring(unittest.TestCase):
    """The composer and New video's description both load the suggest layer."""

    def test_editor_html_loads_suggest_css_and_js(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('<link rel="stylesheet" href="suggest.css">', html)
        self.assertIn('<script src="suggest.js" defer', html)

    def test_editor_composer_markup_suggest_js_hooks_into(self):
        html = (PKG / 'editor.html').read_text()
        self.assertIn('id="composer"', html)
        self.assertIn('class="composer-extras"', html)
        self.assertIn('id="message"', html)

    def test_new_video_page_embeds_suggest_css_and_js(self):
        from videobuilder.pages import new_video_page
        page = new_video_page([]).decode()
        css = (PKG / 'suggest.css').read_text()
        js = (PKG / 'suggest.js').read_text()
        self.assertIn(css, page)
        self.assertIn(js, page)
        self.assertIn('<textarea id="about"', page)


    def test_director_js_clears_suggestions_after_sending_a_note(self):
        js = (PKG / 'director.js').read_text()
        add_pending = re.search(r'async function addPending\(\) \{.*?\n\}', js, re.S).group(0)
        self.assertLess(add_pending.index("$('message').value=''"),
                        add_pending.index("dispatchEvent(new Event('input'"))


if __name__ == '__main__':
    unittest.main()

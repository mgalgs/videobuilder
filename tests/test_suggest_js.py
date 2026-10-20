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
    """The composer and New video both load the suggest layer, and a Look
    pick sets New video's own Look field (suggest-notes.md's q2)."""

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

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_look_pick_sets_new_videos_look_field(self):
        """suggest.js runs in its own <script>, separate from new_video.js's IIFE, so it
        can't reach ST/D/draw directly -- it must go through the window.nvSetLook hook
        new_video.js exposes. Run both sides for real (under node) rather than grepping
        source text, so a wiring break (like the dead `typeof ST !== 'undefined'` check
        this once was) actually fails the test.

        The hook must never call the full draw(): that rebuilds #parts from scratch,
        which would tear out the #about textarea suggest.js's pick() just rewrote (and
        is about to flash) -- killing focus and the undo stack. It should only touch
        the Look part's own body (when open) and the summaries."""
        nv_js = (PKG / 'new_video.js').read_text()
        hook = re.search(r'\nwindow\.nvSetLook=.*?;\n', nv_js).group(0)
        sg_js = (PKG / 'suggest.js').read_text()
        key_of = re.search(r'\nconst keyOf = .*?;', sg_js).group(0)
        apply_look_pick = re.search(r'\nfunction applyLookPick\(i\) \{.*?\n\}', sg_js, re.S).group(0)
        self.assertIn('window.nvSetLook', apply_look_pick)

        script = f"""
const window = {{}};
let ST = {{look: null, open: {{}}}};
const D = {{looks: [{{id: 'pop-art'}}, {{id: 'as-shot'}}]}};
let draws = 0, summaryDraws = 0, lookBodyDraws = 0;
function draw() {{ draws++ }}
function drawSummaries() {{ summaryDraws++ }}
function isOpen(id) {{ return !!ST.open[id] }}
function lookBody() {{ lookBodyDraws++; return '<div>look body</div>' }}
const lookSectionBody = {{innerHTML: ''}};
const lookSection = {{querySelector: sel => sel === '.body' ? lookSectionBody : null}};
function $(sel) {{ return sel === '#part-look' ? lookSection : null }}
{hook}
const NEW = true;
const BY = {{'looks:look-pop-art': {{look: 'pop-art'}}, 'looks:look-paper': {{look: null}}}};
{key_of}
{apply_look_pick}
applyLookPick({{family: 'looks', id: 'look-pop-art'}});
const afterSceneLook = {{look: ST.look, draws, summaryDraws, lookBodyDraws, bodyHtml: lookSectionBody.innerHTML}};
applyLookPick({{family: 'looks', id: 'look-paper'}});
const afterFilterLook = {{look: ST.look, draws, summaryDraws}};
applyLookPick({{family: 'fonts', id: 'cantarell'}});
const afterOtherFamily = {{look: ST.look, draws, summaryDraws}};
ST.open.look = true;
applyLookPick({{family: 'looks', id: 'look-pop-art'}});
const afterOpenLookPart = {{draws, summaryDraws, lookBodyDraws, bodyHtml: lookSectionBody.innerHTML}};
console.log(JSON.stringify({{afterSceneLook, afterFilterLook, afterOtherFamily, afterOpenLookPart}}));
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        # ST.look is set, the summaries are refreshed, but the Look part's own body is left
        # alone while closed -- and critically, draw() (which would rebuild #about) never runs.
        self.assertEqual(out['afterSceneLook'],
                          {'look': 'pop-art', 'draws': 0, 'summaryDraws': 1, 'lookBodyDraws': 0, 'bodyHtml': ''})
        # A filter look (or any id not in D.looks) is ignored: the hook never fires -- and
        # here there's no look id (BY's `look` is None) for the paper-collage entry at all.
        self.assertEqual(out['afterFilterLook'], {'look': 'pop-art', 'draws': 0, 'summaryDraws': 1})
        self.assertEqual(out['afterOtherFamily'], {'look': 'pop-art', 'draws': 0, 'summaryDraws': 1})
        # With the Look part open, the hook refreshes its body too -- still without draw().
        self.assertEqual(out['afterOpenLookPart'],
                          {'draws': 0, 'summaryDraws': 2, 'lookBodyDraws': 1, 'bodyHtml': '<div>look body</div>'})

    def test_director_js_clears_suggestions_after_sending_a_note(self):
        js = (PKG / 'director.js').read_text()
        add_pending = re.search(r'async function addPending\(\) \{.*?\n\}', js, re.S).group(0)
        self.assertLess(add_pending.index("$('message').value=''"),
                        add_pending.index("dispatchEvent(new Event('input'"))


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
from unittest import mock

from videobuilder.capabilities.ui import _code_pane_highlight as highlight

try:
    import pygments  # noqa: F401
    HAVE_PYGMENTS = True
except ImportError:   # an optional extra: the gated image may not have it
    HAVE_PYGMENTS = False

CODE = ''.join(f'def f{i}(x):\n\treturn x + {i}\n' for i in range(40))


@unittest.skipUnless(HAVE_PYGMENTS, 'Pygments (optional) is not installed')
class TestHighlight(unittest.TestCase):
    """Ported from git-video's editor tests: highlighting is lexed and cached
    independently of the pane."""

    def test_highlight_cache_and_tabs(self):
        a = highlight.highlight_lines(CODE, 'a.py')
        self.assertIs(a, highlight.highlight_lines(CODE, 'a.py'))
        self.assertEqual(''.join(s for _, s in a[1]), '    return x + 0')
        self.assertEqual(len(a), 80)
        tok = highlight.tokens_by_line('a\tb\n', 'x.txt')
        self.assertEqual(''.join(s for _, s in tok[0]), 'a   b')

    def test_plain_text_fallback(self):
        self.assertEqual(highlight.lexer_for('README.unknownext').name, 'Text only')

    def test_theme_is_public(self):
        from pygments.token import Token
        self.assertEqual(highlight.THEME[Token.Keyword], '#c678dd')


class TestNoPygments(unittest.TestCase):
    """The pane must still work when Pygments (an optional extra) is not
    installed: one plain colour per line instead of a crash."""

    def setUp(self):
        # block the import outright, even though a lexer module may already be cached
        # in sys.modules from TestHighlight's own tests earlier in this run
        blocked = {m: None for m in sys.modules if m == 'pygments' or m.startswith('pygments.')}
        blocked['pygments'] = None
        self.patcher = mock.patch.dict(sys.modules, blocked)
        self.patcher.start()
        highlight.lexer_for.cache_clear()
        highlight._tokens.cache_clear()
        highlight._runs.cache_clear()

    def tearDown(self):
        self.patcher.stop()
        highlight.lexer_for.cache_clear()
        highlight._tokens.cache_clear()
        highlight._runs.cache_clear()

    def test_lexer_for_is_none(self):
        self.assertIsNone(highlight.lexer_for('x.py'))

    def test_highlight_lines_falls_back_to_one_plain_run_per_line(self):
        runs = highlight.highlight_lines('def f():\n\treturn 1\n\n', 'x.py')
        self.assertEqual(len(runs), 3)
        self.assertEqual(runs[0], ((highlight.FG, 'def f():'),))
        self.assertEqual(runs[1], ((highlight.FG, '    return 1'),))
        self.assertEqual(runs[2], ())   # the blank line stays empty, like the real lexer's

    def test_tabs_still_expand_without_a_lexer(self):
        tok = highlight.tokens_by_line('a\tb\n', 'x.txt')
        self.assertEqual(''.join(s for _, s in tok[0]), 'a   b')


class TestCodePaneExportsHighlight(unittest.TestCase):
    """Callers highlight through code_pane, never the private helper module."""

    def test_names(self):
        from videobuilder.capabilities.ui import code_pane
        for name in ('TAB', 'color_of', 'highlight_lines', 'lexer_for', 'tokens_by_line'):
            self.assertIs(getattr(code_pane, name), getattr(highlight, name))
        if HAVE_PYGMENTS:
            self.assertIs(code_pane.THEME, highlight.THEME)
        with self.assertRaises(AttributeError):
            code_pane.no_such_name


if __name__ == '__main__':
    unittest.main()

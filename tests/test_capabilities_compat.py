"""The operator's decision: there is one word for the thing videobuilder's
registry calls a capability -- never the old one. This checks the repo never
backslides: the sole exception is the compatibility shim at
videobuilder/techniques/__init__.py (so a film written before the rename
keeps resolving its old dotted imports), and this file, which names that
exception and exercises the shim directly.
"""
import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THIS_FILE = Path(__file__).resolve().relative_to(ROOT).as_posix()
SHIM = 'videobuilder/techniques/__init__.py'
# The shim's dotted module path, derived from SHIM above rather than spelled out again.
_SHIM_MODULE = SHIM.rsplit('/', 1)[0].replace('/', '.')

# Built without writing the old word itself, so this test passes on its own source.
_NEEDLE = 'qinhcet'[::-1]
# Ditto for the old record class name the shim aliases.
_OLD_CLASS_NAME = 'euqinhceT'[::-1]


class NoLeftoverName(unittest.TestCase):
    def test_no_tracked_file_names_the_old_word(self):
        files = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True,
                               check=True).stdout.splitlines()
        offenders = []
        for rel in files:
            if rel in (SHIM, THIS_FILE):
                continue
            try:
                text = (ROOT / rel).read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue  # a binary asset, not a text file
            if _NEEDLE in text.lower():
                offenders.append(rel)
        self.assertEqual(offenders, [])


class Compatibility(unittest.TestCase):
    """The module at SHIM is now only a compatibility shim (see its own
    module docstring): a film written before the rename may still use its old
    dotted paths, so those must keep resolving. Reached only via SHIM/
    _SHIM_MODULE above and dynamic attribute lookups, so this class itself
    never has to spell the old word out."""

    def test_old_dotted_module_path_still_imports_and_resolves(self):
        mod = importlib.import_module(f'{_SHIM_MODULE}.principles.follow_through')
        self.assertTrue(callable(mod.follow_through))
        new_mod = importlib.import_module('videobuilder.capabilities.principles.follow_through')
        self.assertIs(mod, new_mod)  # the alias, not a second copy of the module

    def test_old_class_name_aliases_the_new_one(self):
        shim = importlib.import_module(_SHIM_MODULE)
        from videobuilder.capabilities.schema import Capability
        self.assertIs(getattr(shim, _OLD_CLASS_NAME), Capability)

    def test_old_package_name_answers_the_same_registry(self):
        shim = importlib.import_module(_SHIM_MODULE)
        from videobuilder.capabilities import registry
        self.assertEqual(set(shim.ids()), set(registry.ids()))


if __name__ == '__main__':
    unittest.main()

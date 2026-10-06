#!/usr/bin/env python3
"""Check that videobuilder can run here, and say how to fix what's missing.

    python doctor.py

Checks Python 3.11+, ffmpeg and ffprobe, pycairo, PyGObject with Pango and
PangoCairo, Pillow, and that `import videobuilder` works. When videobuilder
isn't importable, it prints the PYTHONPATH (or `pip install -e`) for the
checkout this skill lives in. Exit status 1 if anything is missing.
"""
import importlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent  # <repo>/skill/make-a-video/scripts/doctor.py

HINTS = {
    'arch': 'sudo pacman -S python python-cairo python-gobject python-pillow pango ffmpeg',
    'debian': 'sudo apt install python3 python3-cairo python3-gi python3-pil gir1.2-pango-1.0 ffmpeg',
    'mac': 'brew install python pango pygobject3 py3cairo ffmpeg',
}


def distro():
    if platform.system() == 'Darwin':
        return 'mac'
    try:
        text = Path('/etc/os-release').read_text().lower()
    except OSError:
        return None
    if 'arch' in text:
        return 'arch'
    if 'debian' in text or 'ubuntu' in text:
        return 'debian'
    return None


def main():
    missing = []

    def check(name, fn):
        try:
            detail = fn()
            print(f'  ok       {name}' + (f': {detail}' if detail else ''))
        except Exception as e:  # noqa: BLE001 - report anything
            print(f'  MISSING  {name}: {e}')
            missing.append(name)

    def python():
        if sys.version_info < (3, 11):
            raise RuntimeError(f'Python {platform.python_version()}; videobuilder needs 3.11+')
        return f'{platform.python_version()} ({sys.executable})'

    def tool(t):
        def fn():
            path = shutil.which(t)
            if not path:
                raise RuntimeError('not on PATH')
            out = subprocess.run([t, '-version'], capture_output=True, text=True).stdout.splitlines()
            return out[0] if out else path
        return fn

    def module(m, attr=None):
        def fn():
            mod = importlib.import_module(m)
            return getattr(mod, attr, '') if attr else ''
        return fn

    def pango():
        import gi
        gi.require_version('Pango', '1.0')
        gi.require_version('PangoCairo', '1.0')
        from gi.repository import Pango, PangoCairo  # noqa: F401
        return f'Pango {Pango.version_string()}'

    def videobuilder():
        try:
            import videobuilder as vb
        except ImportError:
            if (REPO / 'videobuilder' / '__init__.py').exists():
                sys.path.insert(0, str(REPO))
                import videobuilder as vb  # noqa: F401
                raise RuntimeError(f'not installed, but the checkout at {REPO} works: run films with\n'
                                   f'             PYTHONPATH={REPO}\n'
                                   f'           or install it: pip install -e {REPO}')
            raise
        return str(Path(vb.__file__).resolve().parent)

    print('videobuilder doctor:')
    check('python', python)
    check('ffmpeg', tool('ffmpeg'))
    check('ffprobe', tool('ffprobe'))
    check('pycairo', module('cairo', 'version'))
    check('PyGObject + Pango', pango)
    check('Pillow', module('PIL', '__version__'))
    if not set(missing) & {'pycairo', 'PyGObject + Pango', 'Pillow'}:
        check('videobuilder', videobuilder)
    if set(missing) - {'videobuilder'}:
        d = distro()
        print('\nTo install the system packages' + (f' ({d}):' if d else ' (see README.md, "Install"):'))
        for k, cmd in HINTS.items():
            if d is None or k == d:
                print(f'  {k}: {cmd}' if d is None else f'  {cmd}')
        print('In a virtualenv, make it with `python -m venv --system-site-packages` so it sees the distro\'s '
              'pycairo and PyGObject.')
    if missing:
        return 1
    print('all good')
    return 0


if __name__ == '__main__':
    sys.exit(main())

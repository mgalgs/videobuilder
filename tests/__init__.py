import os
import tempfile
from pathlib import Path

# Every test, and every film a test renders in a child process, reads the checked-in fixture pack of
# sound effects (a few tiny takes), never the real pack a machine may have installed.
os.environ['VIDEOBUILDER_SFX_DIR'] = str(Path(__file__).resolve().parent / 'fixtures' / 'sfx-pack')
# Sound stems (`videobuilder.stem`) go to the temp dir, not the user's cache.
os.environ['VIDEOBUILDER_STEM_DIR'] = os.path.join(tempfile.gettempdir(), 'videobuilder-test-stems')
# No test reaches the real Gemini: one that wants it points GEMINI_API_KEY and the URL at tests/fake_gemini.py.
os.environ.pop('GEMINI_API_KEY', None)

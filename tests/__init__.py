import os
from pathlib import Path

# Every test, and every film a test renders in a child process, reads the checked-in fixture pack of
# sound effects (a few tiny takes), never the real pack a machine may have installed.
os.environ['VIDEOBUILDER_SFX_DIR'] = str(Path(__file__).resolve().parent / 'fixtures' / 'sfx-pack')

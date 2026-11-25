import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class FlockPreparationTest(unittest.TestCase):
    def test_unpinned_checkout_fails_before_building(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            checkouts = work / 'sources'
            checkouts.mkdir()
            (checkouts / 'mato').symlink_to(ROOT, target_is_directory=True)
            result = subprocess.run(
                ['bash', str(ROOT / 'flock/launch.sh'), 'prepare'], cwd=ROOT,
                env={**os.environ, 'FLOCK_ROOT': str(checkouts), 'FLOCK_DATA_ROOT': directory,
                     'MS2KG_WORK': directory, 'MS2KG_INPUT': directory, 'MS2KG_ROOT': str(ROOT)},
                capture_output=True, text=True, timeout=15,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Expected mato at fc449d1ff4207ce07d4bef2120d2b2bd50cc1037', result.stderr)

import tempfile
import unittest
from pathlib import Path

from benchmark_input import INPUT_DIGESTS, verify_input


class CanonicalInputTest(unittest.TestCase):
    def test_input_verification_rejects_preprocessed_files_and_changed_raw_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in INPUT_DIGESTS:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'changed')
            extra = root / 'msdata/processed/features.mgf'
            extra.parent.mkdir()
            extra.write_bytes(b'derived')
            with self.assertRaisesRegex(ValueError, 'unexpected.*msdata/processed/features.mgf'):
                verify_input(root)
            extra.unlink()
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                verify_input(root)

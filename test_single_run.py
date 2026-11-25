import csv
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from rdflib import Graph, RDF
from rdflib.namespace import SOSA

import benchmark_input
from pipeline import run_comparison
from test_chemicals_enpkg import chemical_trial
from test_chemicals_flock import flock_fixture


class SingleRunTest(unittest.TestCase):
    def test_raw_to_validated_reports_from_one_process_per_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            enpkg = root / 'enpkg'
            flock = root / 'flock'
            enpkg.mkdir()
            flock.mkdir()
            chemical_trial(enpkg)
            flock_fixture(flock)
            with sqlite3.connect(flock / 'flock/toy.sqlite') as store:
                store.execute('ATTACH DATABASE ? AS samples', (str(enpkg / 'flock/toy.sqlite'),))
                for table in ('datasets', 'sample_rows', 'spectrum_files', 'taxa', 'taxon_resolutions'):
                    store.execute(f'DELETE FROM main.{table}')
                    store.execute(f'INSERT INTO main.{table} SELECT * FROM samples.{table}')
                store.execute('UPDATE annotation_runs SET dataset_id = 12')

            archive = root / 'release.zip'
            inputs = {name: name.encode() for name in benchmark_input.INPUT_DIGESTS}
            inputs['metadata/metadata.tsv'] = (enpkg / 'metadata.tsv').read_bytes()
            with ZipFile(archive, 'w') as release:
                for name, data in inputs.items():
                    release.writestr(name, data)
            digests = {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()}

            profiles = root / 'profiles'
            profiles.mkdir()
            call_log = root / 'calls'
            for evidence in (enpkg, flock):
                native = evidence / 'native'
                native.mkdir()
                for filename in ('one.nq', 'two.nq'):
                    (native / filename).write_text(
                        '<urn:s> <urn:p> "same" <urn:g1> .\n'
                        '<urn:s> <urn:p> "same" <urn:g2> .\n'
                        '_:b <urn:p> "local" <urn:g1> .\n'
                        '<urn:s> <urn:p> "01"^^<http://www.w3.org/2001/XMLSchema#integer> <urn:g1> .\n'
                        '<urn:s> <urn:p> "1"^^<http://www.w3.org/2001/XMLSchema#integer> <urn:g1> .\n'
                    )
                command = [sys.executable, '-c', 'import os, shutil, sys\nfrom pathlib import Path\n'
                           'shutil.copytree(sys.argv[1], os.environ["MS2KG_WORK"], dirs_exist_ok=True)\n'
                           'with open(sys.argv[2], "a") as log: print(Path(sys.argv[1]).name, os.environ["MS2KG_INPUT"], file=log)',
                           str(evidence), str(call_log)]
                (profiles / f'{evidence.name}.toml').write_text(f'command = {json.dumps(command)}\nrdf = ["native/*.nq"]\n')

            with patch.dict(os.environ, ENPKG_ARCHIVE=str(archive)), patch.object(benchmark_input, 'INPUT_DIGESTS', digests), patch.object(benchmark_input, 'DATASET_SHA256', benchmark_input.sha256(archive)):
                workspace = run_comparison(root / 'runs', profiles)
            self.assertEqual(call_log.read_text().splitlines(), [f'{name} {workspace / "input"}' for name in ('enpkg', 'flock')])
            with (workspace / 'comparison.tsv').open() as stream:
                rows = list(csv.DictReader(stream, delimiter='\t'))
            self.assertEqual([row['pipeline'] for row in rows], ['enpkg', 'flock'])
            for row, observations in zip(rows, (4, 3), strict=True):
                self.assertEqual(int(row['native_distinct_triples']), 5)
                trial = workspace / row['pipeline']
                self.assertEqual([path.name for path in trial.glob('*.ttl')], ['reconciled.ttl'])
                graph = Graph().parse(trial / 'reconciled.ttl')
                self.assertEqual(int(row['reconciled_distinct_triples']), len(graph))
                self.assertEqual(len(set(graph.subjects(RDF.type, SOSA.Observation))), observations)
                self.assertTrue(any(graph.subjects(RDF.type, SOSA.Sample)))
                for prefix in ('', 'reconciliation_'):
                    self.assertGreaterEqual(float(row[prefix + 'wall_seconds']), 0)
                    self.assertGreater(int(row[prefix + 'peak_rss_kib']), 0)
            for report in ('pair-summary.md', 'pair-evidence.tsv'):
                self.assertTrue((workspace / report).is_file())

    def test_changed_input_stops_before_the_next_trial_and_keeps_private_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'release.zip'
            with ZipFile(archive, 'w') as release:
                release.writestr('raw', b'original')
            digests = {'raw': hashlib.sha256(b'original').hexdigest()}
            command = [sys.executable, '-c', 'import os; from pathlib import Path; (Path(os.environ["MS2KG_INPUT"]) / "raw").write_text("changed")']
            (root / 'enpkg.toml').write_text(f'command = {json.dumps(command)}\nrdf = ["native.ttl"]\n')
            with patch.dict(os.environ, ENPKG_ARCHIVE=str(archive)), patch.object(benchmark_input, 'INPUT_DIGESTS', digests), patch.object(benchmark_input, 'DATASET_SHA256', benchmark_input.sha256(archive)):
                with self.assertRaisesRegex(ValueError, 'checksum mismatch for raw'):
                    run_comparison(root / 'runs', root)
            workspace, = (root / 'runs').iterdir()
            self.assertEqual(workspace.stat().st_mode & 0o077, 0)
            self.assertTrue((workspace / 'enpkg/native.log').is_file())
            self.assertFalse((workspace / 'flock').exists())
            self.assertFalse((workspace / 'comparison.tsv').exists())

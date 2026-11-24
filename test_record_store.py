import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import recover
from record_store import local_records, publish


class RecordStoreTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.build = Path(directory.name)

    def snapshot(self, identifier):
        record = self.build / f'enpkg.{identifier}/record/enpkg'
        record.mkdir(parents=True)
        (record / 'README.md').write_text(identifier)
        (record / 'benchmark.json').write_text('{}')
        return record

    def test_interrupted_publication_keeps_prior_selection_and_both_snapshots(self):
        first = self.snapshot('one')
        second = self.snapshot('two')
        legacy = self.build / 'records/flock'
        legacy.mkdir(parents=True)
        publish(self.build, first)
        with patch('record_store.os.replace', side_effect=OSError('interrupted')), self.assertRaises(OSError):
            publish(self.build, second)
        self.assertEqual(local_records(self.build), [first, legacy])
        publish(self.build, second)
        self.assertEqual(local_records(self.build), [second, legacy])
        self.assertEqual((first / 'README.md').read_text(), 'one')

    def test_invalid_pointer_fails_without_legacy_fallback(self):
        valid = self.snapshot('one')
        publish(self.build, valid)
        (self.build / 'records/enpkg').mkdir(parents=True)
        pointer = self.build / 'latest/enpkg'
        for invalid in ('../escape', str(valid), 'flock.one/record/enpkg', 'enpkg.one/record/flock', 'enpkg.one//record/enpkg'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                pointer.write_text(invalid)
                local_records(self.build)
        pointer.unlink()
        pointer.symlink_to(valid / 'README.md')
        with self.assertRaises(ValueError):
            local_records(self.build)

    def test_workspace_symlink_is_rejected(self):
        valid = self.snapshot('one')
        publish(self.build, valid)
        workspace = valid.parents[1]
        workspace.rename(self.build / 'outside')
        workspace.symlink_to(self.build / 'outside')
        with self.assertRaises(ValueError):
            local_records(self.build)

    def test_recovery_requires_original_cohort_before_reading_trials(self):
        workspace = self.build / 'enpkg.old'
        workspace.mkdir()
        with self.assertRaisesRegex(ValueError, '--cohort'):
            recover(self.build, workspace)

    def test_recovery_rejects_mislabeled_existing_record(self):
        record = self.snapshot('old')
        with patch('pipeline.read_report', return_value={'cohort': 'original'}):
            with self.assertRaisesRegex(ValueError, 'original'):
                recover(self.build, record.parents[1], 'another')
            recover(self.build, record.parents[1])
        self.assertEqual(local_records(self.build), [record])

    def test_recovery_rejects_snapshot_from_another_pipeline(self):
        record = self.snapshot('wrong')
        with patch('pipeline.read_report', return_value={'cohort': 'original', 'pipeline': 'flock'}):
            with self.assertRaisesRegex(ValueError, 'flock'):
                recover(self.build, record.parents[1])
        self.assertEqual(local_records(self.build), [])

    def test_replay_builds_a_complete_snapshot_without_running_the_profile(self):
        workspace = self.build / 'enpkg.recovered'
        workspace.mkdir()
        (workspace / 'profile.toml').write_text('command = ["do-not-run"]\nrdf = ["graph.ttl"]\n')
        (workspace / 'cohort.txt').write_text('original\n')
        for trial in ('first', 'second'):
            (workspace / trial).mkdir()
            (workspace / trial / 'graph.ttl').write_text('<urn:a> <urn:b> <urn:c> .')

        def record(arguments, **options):
            self.assertEqual(arguments[3], 'record')
            self.assertEqual(arguments[arguments.index('--cohort') + 1], 'original')
            self.assertEqual(arguments[arguments.index('--pipeline') + 1], 'enpkg')
            directory = arguments[arguments.index('--submission') + 1]
            (directory / 'benchmark.json').write_text('{}')

        with patch('pipeline.subprocess.run', side_effect=record) as process, patch('pipeline.read_report'):
            recover(self.build, workspace)
            process.assert_called_once()
        snapshot, = local_records(self.build)
        self.assertEqual(snapshot, workspace / 'record/enpkg')
        self.assertIn('do-not-run', (snapshot / 'README.md').read_text())

    def test_replay_preserves_partial_runbook_and_only_publishes_validated_record(self):
        partial = self.snapshot('partial')
        workspace = partial.parents[1]
        report = partial / 'benchmark.json'
        report.unlink()
        (workspace / 'profile.toml').write_text('rdf = ["graph.ttl"]')
        for trial in ('first', 'second'):
            (workspace / trial).mkdir()
            (workspace / trial / 'graph.ttl').touch()

        def record(arguments, **options):
            directory = arguments[arguments.index('--submission') + 1]
            (directory / 'benchmark.json').write_text('{}')

        with patch('pipeline.subprocess.run', side_effect=record):
            with self.assertRaises(ValueError):
                recover(self.build, workspace, 'original')
            self.assertFalse(report.exists())
            self.assertEqual(local_records(self.build), [])
            with patch('pipeline.read_report', return_value={'cohort': 'original'}):
                recover(self.build, workspace, 'original')
        self.assertEqual(local_records(self.build), [partial])
        self.assertEqual((partial / 'README.md').read_text(), 'partial')

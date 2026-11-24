import tempfile
import json
import os
import re
import subprocess
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from benchmark import load_rdf, read_gnu_time, same_rdf, write_comparison, write_report
from record_store import check_submission_directory
from benchmark_input import INPUT_DIGESTS, verify_input


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def fixture(self, name, content):
        path = self.directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_timing_keeps_hours_and_rejects_failed_commands(self):
        timing = (
            "\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02:03.50\n"
            "\tMaximum resident set size (kbytes): 8192\n"
        )
        path = self.fixture("time.txt", timing + "\tExit status: 0\n")
        self.assertEqual(read_gnu_time(path), {"wall_seconds": 3723.5, "peak_rss_kib": 8192})
        path.write_text(timing + "\tExit status: 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exit status 1"):
            read_gnu_time(path)

    def test_rdf_union_deduplicates_triples_and_scopes_blank_nodes_per_file(self):
        triples = '<urn:s> <urn:p> _:label .\n<urn:s> <urn:q> "same" .\n'
        first = self.fixture("first.ttl", triples)
        second = self.fixture("second.ttl", triples)
        dataset = load_rdf([first, second])
        self.assertEqual(len(set(dataset.triples((None, None, None)))), 3)

    def test_flock_counts_quads_separately_and_keeps_literal_lexical_forms(self):
        datatype = "http://www.w3.org/2001/XMLSchema#integer"
        first = f'<urn:s> <urn:p> "01"^^<{datatype}>'
        second = f'<urn:s> <urn:p> "1"^^<{datatype}>'
        graph = self.fixture(
            "graph.nq", f"{first} .\n{first} <urn:g> .\n{second} <urn:g> .\n{second} <urn:g> .\n"
        )
        dataset = load_rdf([graph])
        self.assertEqual(len(set(dataset.triples((None, None, None)))), 2)
        self.assertEqual(len(set(dataset.quads())), 3)
        self.assertEqual(len(dataset.default_graph), 1)

    def test_repeatability_respects_blank_node_identity_and_named_graphs(self):
        first = self.fixture("first.nq", "_:item <urn:p> <urn:a> <urn:g> .\n_:item <urn:p> <urn:b> .\n")
        equivalent = self.fixture("second.nq", "_:renamed <urn:p> <urn:b> .\n_:renamed <urn:p> <urn:a> <urn:g> .\n")
        different = self.fixture("third.nq", "_:renamed <urn:p> <urn:b> .\n_:renamed <urn:p> <urn:a> .\n")
        self.assertTrue(same_rdf(load_rdf([first]), load_rdf([equivalent])))
        self.assertFalse(same_rdf(load_rdf([first]), load_rdf([different])))

    def test_input_verification_rejects_preprocessed_files_and_changed_raw_bytes(self):
        for name in INPUT_DIGESTS:
            path = self.directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"changed")
        extra = self.directory / "msdata/processed/features.mgf"
        extra.parent.mkdir()
        extra.write_bytes(b"derived")
        with self.assertRaisesRegex(ValueError, "unexpected.*msdata/processed/features.mgf"):
            verify_input(self.directory)
        extra.unlink()
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_input(self.directory)

    def submission(self, root, name, cohort="host-a", seconds=8, schema=3):
        submission = root / name
        submission.mkdir(parents=True)
        (submission / "README.md").write_text("# Runbook\n", encoding="utf-8")
        payload = {
            "schema": schema,
            "pipeline": "enpkg",
            "rdf_equivalent": False,
            "cohort": cohort,
            "dataset_sha256": "0c8bc4f8d350999a5b2910774e00cd4731ea32ffacbf2c0828258966583ed450",
            "input_sha256": INPUT_DIGESTS,
            "trials": [
                {"timing": {"wall_seconds": elapsed, "peak_rss_kib": 4096}, "rdf": [
                    {"name": "graph.ttl", "bytes": 100, "sha256": "a" * 64}
                ], "timing_sha256": "b" * 64, "graph": dict(triples=12 + number, quads=12 + number,
                    subjects=3, objects=7, predicates=2, classes=1, blank_nodes=0, named_graphs=0)}
                for number, elapsed in enumerate((seconds - 1, seconds + 1))
            ],
        }
        if schema == 2:
            del payload["rdf_equivalent"]
            payload["graph"] = payload["trials"][0].pop("graph")
            del payload["trials"][1]["graph"]
        record = submission / "benchmark.json"
        record.write_text(json.dumps(payload), encoding="utf-8")
        return record

    def linked_charts(self, output):
        markdown = (output / "comparison.md").read_text(encoding="utf-8")
        return {Path(link).name: output / link for link in re.findall(r"!\[[^\]]+\]\(([^)]+\.svg)\)", markdown)}

    def test_compare_groups_timing_by_cohort_and_renders_graph_metrics(self):
        root = self.directory / "submissions"
        local = self.directory / "local"
        self.submission(root, "first")
        self.submission(local, "second", seconds=2)
        self.submission(local, "third", cohort="host-b", seconds=1, schema=2)
        output = self.directory / "build"
        result = subprocess.run(
            [sys.executable, "-B", "benchmark.py", "compare", "--submissions", root,
             "--local-submissions", local, "--output", output],
            capture_output=True, text=True, check=True, timeout=10,
        )
        self.assertIn("3 submission", result.stdout)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        charts = self.linked_charts(output)
        time = ElementTree.parse(charts["timing-host-a.svg"])
        row = time.find(".//svg:g[@aria-label='Wall time (s)']", namespace)
        values = lambda panel: [node.text for node in panel.findall("svg:text[@class='value']", namespace)]
        self.assertEqual(values(row), ["7.00", "9.00", "1.00", "3.00"])
        bars = row.findall("svg:rect", namespace)
        self.assertAlmostEqual(float(bars[2].get("width")) / float(bars[1].get("width")), 1 / 9)
        self.assertNotIn("third", ElementTree.tostring(time.getroot(), encoding="unicode"))
        self.assertTrue(charts["timing-host-b.svg"].is_file())
        chart = ElementTree.parse(charts["graph.svg"])
        triples = chart.find(".//svg:g[@aria-label='Distinct triples']", namespace)
        self.assertEqual(values(triples), ["12", "13", "12", "13", "12", "12"])
        comparison = (output / "comparison.md").read_text()
        self.assertIn("| first | Submitted | non-equivalent |", comparison)
        self.assertIn("| third | Local | equivalent |", comparison)

        (local / "second").rename(local / "first")
        workspace = output / "work" / "keep"
        workspace.parent.mkdir()
        workspace.write_bytes(b"private")
        unrelated = output / "timing-unrelated.svg"
        unrelated.write_bytes(b"unrelated")
        subprocess.run(result.args, capture_output=True, text=True, timeout=10, check=True)
        comparison = (output / "comparison.md").read_text()
        self.assertIn("| first | Submitted |", comparison)
        self.assertIn("| first | Local |", comparison)
        self.assertEqual(workspace.read_bytes(), b"private")
        self.assertEqual(unrelated.read_bytes(), b"unrelated")

    def test_preview_follows_latest_snapshot_and_links_its_evidence(self):
        root = self.directory / "submissions"
        build = self.directory / "build"
        self.submission(root, "enpkg")
        self.submission(build / "records", "enpkg", cohort="legacy")
        current = self.submission(build / "enpkg.current/record", "enpkg", cohort="latest")
        latest = build / "latest"
        latest.mkdir()
        (latest / "enpkg").write_text("enpkg.current/record/enpkg\n")
        subprocess.run(
            [sys.executable, "-B", "benchmark.py", "compare", "--submissions", root, "--output", build,
             "--latest", latest, "--local-submissions", build / "records"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        comparison = (build / "comparison.md").read_text()
        self.assertIn("| enpkg | Submitted |", comparison)
        self.assertIn("| enpkg | Local |", comparison)
        self.assertIn(current.relative_to(build).as_posix(), comparison)
        self.assertNotIn("legacy", comparison)

    def test_interruption_before_index_switch_preserves_the_previous_report(self):
        root = self.directory / "submissions"
        output = self.directory / "results"
        self.submission(root, "first")
        args = Namespace(command="publish", submissions=root, output=output, check=False)
        write_comparison(args)
        index = output / "comparison.md"
        original = index.read_bytes()
        charts = {path: path.read_bytes() for path in self.linked_charts(output).values()}
        self.submission(root, "second", cohort="host-b")
        replace = os.replace

        def interrupt_index(source, destination):
            if Path(destination) == index:
                raise OSError("index switch interrupted")
            replace(source, destination)

        with patch("os.replace", side_effect=interrupt_index), self.assertRaisesRegex(OSError, "interrupted"):
            write_comparison(args)
        self.assertEqual(index.read_bytes(), original)
        for path, expected in charts.items():
            self.assertEqual(path.read_bytes(), expected)
        write_comparison(args)
        self.assertIn("timing-host-b.svg", self.linked_charts(output))
        self.assertFalse(any(path.exists() for path in charts))

    def test_record_replacement_keeps_prior_json_on_write_failure(self):
        report = self.submission(self.directory / "submissions", "first")
        expected = report.read_bytes()
        timing = "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:09.5\nMaximum resident set size (kbytes): 8\nExit status: 0\n"
        triple = "<urn:subject> <urn:predicate> <urn:object> .\n"
        args = Namespace(submission=report.parent, cohort="host-a", pipeline="enpkg", input=self.directory,
                         first_time=self.fixture("first.time", timing), second_time=self.fixture("second.time", timing),
                         first_rdf=[self.fixture("first.nt", triple)], second_rdf=[self.fixture("second.nt", triple)])

        def interrupt(source, destination):
            self.assertEqual(destination, report)
            for directory in report.parent.parent.iterdir():
                check_submission_directory(directory)
            self.assertEqual(report.read_bytes(), expected)
            raise OSError("disk failure")

        with patch("benchmark.verify_input"), patch("os.replace", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "disk failure"):
                write_report(args)
        self.assertEqual(report.read_bytes(), expected)
        self.assertEqual(sorted(entry.name for entry in report.parent.iterdir()), ["README.md", "benchmark.json"])
        with patch("benchmark.verify_input"):
            write_report(args)
        self.assertEqual(json.loads(report.read_bytes())["pipeline"], "enpkg")

    def test_published_results_reproduce_submissions_and_exclude_local_evidence(self):
        root = self.directory / "submissions"
        output = self.directory / "results"
        first = self.submission(root, "first")
        self.submission(self.directory / "build/records", "private")
        command = [sys.executable, "-B", "benchmark.py", "publish", "--submissions", root, "--output", output]

        def publish(*arguments, success=True):
            result = subprocess.run([*command, *arguments], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode == 0, success, result.stderr)

        publish("--check", success=False)
        self.assertFalse(output.exists())
        publish()
        publish("--check")
        index = output / "comparison.md"
        original = index.read_bytes()
        self.assertNotIn(b"private", original)
        self.assertIn(b"](../submissions/first/README.md)", original)
        charts = self.linked_charts(output)
        self.assertEqual(set(charts), {"graph.svg", "timing-host-a.svg"})
        chart = charts["graph.svg"]
        expected = chart.read_bytes()
        chart.write_bytes(b"stale")
        publish("--check", success=False)
        self.assertEqual(chart.read_bytes(), b"stale")
        publish()
        self.assertEqual(chart.read_bytes(), expected)
        self.assertEqual(index.read_bytes(), original)
        chart.unlink()
        publish("--check", success=False)
        publish()
        extra = chart.with_name("timing-obsolete.svg")
        extra.write_bytes(expected)
        publish("--check", success=False)
        publish()
        self.assertFalse(extra.exists())
        index.write_bytes(b"stale index")
        publish("--check", success=False)
        publish()
        foreign = output / "private.txt"
        foreign.write_bytes(b"preserve me")
        publish("--check", success=False)
        publish(success=False)
        self.assertEqual(foreign.read_bytes(), b"preserve me")
        foreign.unlink()

        payload = json.loads(first.read_bytes())
        payload["cohort"] = "host-b"
        first.write_text(json.dumps(payload))
        publish("--check", success=False)
        publish()
        self.assertFalse(charts["timing-host-a.svg"].exists())
        self.assertIn("timing-host-b.svg", self.linked_charts(output))
        publish("--check")

    def test_publication_requires_a_runnable_profile_without_executing_it(self):
        root = self.directory / "submissions"
        record = self.submission(root, "first")
        pipelines = self.directory / "pipelines"
        pipelines.mkdir()
        profile = pipelines / "enpkg.toml"
        script = Path(__file__).resolve().with_name("benchmark.py")
        command = [sys.executable, "-B", script, "publish"]

        def run():
            return subprocess.run(command, cwd=self.directory, capture_output=True, text=True, timeout=10)

        self.assertNotEqual(run().returncode, 0)
        target = self.fixture("other.toml", 'command = ["false"]\nrdf = ["*.ttl"]\n')
        profile.symlink_to(target)
        self.assertNotEqual(run().returncode, 0)
        profile.unlink()
        profile.write_text('command = []\nrdf = ["*.ttl"]\n')
        self.assertNotEqual(run().returncode, 0)
        profile.write_text('command = ["false"]\nrdf = []\n')
        self.assertNotEqual(run().returncode, 0)
        profile.write_bytes(target.read_bytes())
        elsewhere = pipelines.rename(self.directory / "external")
        pipelines.symlink_to(elsewhere, target_is_directory=True)
        self.assertNotEqual(run().returncode, 0)
        pipelines.unlink()
        elsewhere.rename(pipelines)
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        command.append("--check")
        payload = json.loads(record.read_bytes())
        for pipeline in (None, "../outside", "unknown"):
            with self.subTest(pipeline=pipeline):
                payload["pipeline"] = pipeline
                record.write_text(json.dumps(payload))
                self.assertNotEqual(run().returncode, 0)
        del payload["pipeline"]
        record.write_text(json.dumps(payload))
        self.assertNotEqual(run().returncode, 0)

    def test_compare_accepts_missing_local_directory(self):
        root = self.directory / "submissions"
        root.mkdir()
        output = self.directory / "build"
        subprocess.run(
            [sys.executable, "-B", "benchmark.py", "compare", "--submissions", root,
             "--local-submissions", self.directory / "missing", "--output", output],
            capture_output=True, text=True, check=True, timeout=10,
        )
        self.assertIn("No benchmark submissions yet.", (output / "comparison.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

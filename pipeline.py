"""Compare fresh ENPKG and Flock trials on one verified raw dataset."""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from zipfile import BadZipFile

import rdflib
from rdflib import Dataset, Graph, Literal, XSD

from benchmark_input import prepare_input, sha256, verify_input
from rdf.compare_pairs import compare
from schema.validate import SCHEMA, validate_graph


ROOT = Path(__file__).resolve().parent
RELEASE = "https://zenodo.org/records/10018590/files/enpkg_toy_dataset.zip?download=1"
RDF_FORMATS = {".ttl": "turtle", ".nt": "nt", ".nq": "nquads", ".trig": "trig"}
HEADER = ("pipeline", "wall_seconds", "peak_rss_kib", "native_distinct_triples",
          "reconciliation_wall_seconds", "reconciliation_peak_rss_kib", "reconciled_distinct_triples")


def strings(profile, field):
    value = profile.get(field)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"Expected a nonempty array of strings for {field}")
    return value


def prepare_dataset(workspace):
    archive = Path(os.environ.get("ENPKG_ARCHIVE", ROOT / "build/enpkg_toy_dataset.zip"))
    if not archive.is_file() and "ENPKG_ARCHIVE" not in os.environ:
        archive = workspace / "enpkg_toy_dataset.zip"
        download = subprocess.run(["curl", "-fLsS", "--max-time", "300", RELEASE, "-o", archive], timeout=310)
        if download.returncode:
            raise ValueError("Save the ZIP from https://zenodo.org/records/10018590 as build/enpkg_toy_dataset.zip and rerun the command.")
    directory = workspace / "input"
    prepare_input(archive, directory)
    return directory, archive.resolve()


def rdf_files(work, patterns):
    files = set()
    for pattern in patterns:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ValueError(f"RDF pattern must be relative to the trial directory: {pattern}")
        matches = sorted(work.glob(pattern))
        if not matches or any(not path.is_file() or not path.resolve().is_relative_to(work) for path in matches):
            raise ValueError(f"Expected RDF files under {work} matching {pattern}")
        files.update(matches)
    return sorted(files)


def distinct_native_triples(paths):
    """Count the union of RDF triples, scoping blank nodes to each document."""
    triples = set()
    normalize_literals = rdflib.NORMALIZE_LITERALS
    try:
        rdflib.NORMALIZE_LITERALS = False
        for path in paths:
            syntax = RDF_FORMATS.get(path.suffix.lower())
            if syntax is None:
                raise ValueError(f"Unsupported RDF file extension in {path}")
            document = Dataset(default_union=True)
            document.parse(path, format=syntax)
            for subject, predicate, value in document.triples((None, None, None)):
                if isinstance(value, Literal) and value.datatype == XSD.string:
                    value = Literal(str(value), normalize=False)
                triples.add((subject, predicate, value))
    finally:
        rdflib.NORMALIZE_LITERALS = normalize_literals
    if not triples:
        raise ValueError("Native RDF contains no triples")
    return len(triples)


def measured(command, trial, stage, environment):
    timing = trial / f"{stage}-time.tsv"
    log = trial / f"{stage}.log"
    with log.open("xb") as stream:
        subprocess.run(["/usr/bin/time", "-f", "%e\t%M", "-o", timing, "--", *command],
                       cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=86400)
    seconds, peak = timing.read_text(encoding="ascii").strip().split("\t")
    return float(seconds), int(peak)


def run_trial(name, trial, profile_path, directory, archive, shapes):
    trial.mkdir()
    config = trial / "profile.toml"
    shutil.copyfile(profile_path, config)
    profile = tomllib.loads(config.read_text(encoding="utf-8"))
    if unknown := set(profile) - {"command", "prepare", "rdf", "settings"}:
        raise ValueError(f"Unknown profile fields: {sorted(unknown)}")
    command, patterns = strings(profile, "command"), strings(profile, "rdf")
    environment = dict(os.environ, MS2KG_ROOT=str(ROOT), MS2KG_INPUT=str(directory),
                       MS2KG_WORK=str(trial), MS2KG_CONFIG=str(config), LC_ALL="C")
    if "prepare" in profile:
        with (trial / "prepare.log").open("xb") as stream:
            subprocess.run(strings(profile, "prepare"), cwd=ROOT, env={**environment, "MS2KG_ARCHIVE": str(archive)},
                           stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=86400)
    verify_input(directory)
    print(f"Running {name} in {trial}", flush=True)
    native_time = measured(command, trial, "native", environment)
    verify_input(directory)
    native = rdf_files(trial, patterns)
    with (trial / "native.sha256").open("x", encoding="utf-8") as manifest:
        for path in native:
            print(f"{sha256(path)}  {path.relative_to(trial)}", file=manifest)
    native_count = distinct_native_triples(native)
    reconciliation = [sys.executable, "-B", ROOT / "shared_schema.py", name, trial, directory / "metadata/metadata.tsv"]
    reconciliation_time = measured(reconciliation, trial, "reconciliation", environment)
    graph = Graph().parse(trial / "reconciled.ttl", format="turtle")
    validate_graph(graph, shapes)
    return name, *native_time, native_count, *reconciliation_time, len(graph)


def run_comparison(runs=ROOT / "runs", profiles=ROOT / "pipelines"):
    runs = runs.resolve()
    runs.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="run-", dir=runs))
    print(f"Workspace: {workspace}", flush=True)
    directory, archive = prepare_dataset(workspace)
    with (workspace / "input.sha256").open("x", encoding="utf-8") as manifest:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                print(f"{sha256(path)}  {path.relative_to(workspace)}", file=manifest)
    shapes_copy = workspace / SCHEMA.name
    shutil.copyfile(SCHEMA, shapes_copy)
    shapes = Graph().parse(shapes_copy, format="turtle")
    rows = [run_trial(name, workspace / name, profiles / f"{name}.toml", directory, archive, shapes)
            for name in ("enpkg", "flock")]
    compare(workspace, workspace)
    with (workspace / "comparison.tsv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    return workspace


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT / "runs", help="parent directory for fresh workspaces")
    arguments = parser.parse_args()
    os.umask(0o077)
    try:
        run_comparison(arguments.runs)
    except (OSError, ValueError, BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(1, f"Comparison failed: {error}\n")

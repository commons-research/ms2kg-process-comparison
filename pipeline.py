"""Run a configured external pipeline on the canonical benchmark input."""

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from zipfile import BadZipFile

from benchmark import read_report
from benchmark_input import prepare_input, verify_input
from chemical_schema import export_chemicals
from record_store import check_submission_directory, checked_directory, publish, slug, workspace_slug
from shared_schema import READERS as SHARED_READERS, export_trial


ROOT = Path(__file__).resolve().parent
RELEASE = "https://zenodo.org/records/10018590/files/enpkg_toy_dataset.zip?download=1"


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


def recover(build, workspace, cohort=None):
    build = build.absolute()
    workspace = workspace.absolute()
    if workspace.parent != checked_directory(build):
        raise ValueError(f"Expected a workspace directly under {build}")
    name = workspace_slug(checked_directory(workspace))
    parent = workspace / "record"
    parent.mkdir(exist_ok=True)
    record = checked_directory(parent) / name
    if record.is_symlink():
        raise ValueError(f"Unexpected record symlink at {record}")
    if record.exists() and any(record.iterdir()):
        check_submission_directory(record)
    report = record / "benchmark.json"
    if report.exists():
        restored = read_report(report)
        if restored.get("pipeline", name) != name:
            raise ValueError(f"Snapshot identifies pipeline {restored['pipeline']!r}, expected {name!r}")
        original = restored["cohort"]
        if cohort is not None and cohort != original:
            raise ValueError(f"Snapshot already belongs to cohort {original}")
    else:
        saved = workspace / "cohort.txt"
        if saved.exists():
            original = slug(saved.read_text(encoding="utf-8").strip())
            if cohort is not None and cohort != original:
                raise ValueError(f"Workspace already belongs to cohort {original}")
            cohort = original
        if cohort is None:
            raise ValueError("Supply the original --cohort to recover this workspace")
        slug(cohort)
        profile_path = workspace / "profile.toml"
        if not profile_path.exists():
            profile_path = ROOT / "pipelines" / f"{name}.toml"
        profile_text = profile_path.read_text(encoding="utf-8")
        patterns = strings(tomllib.loads(profile_text), "rdf")
        recording = []
        for label in ("first", "second"):
            work = workspace / label
            recording.extend([f"--{label}-time", work / "time.txt", f"--{label}-rdf", *rdf_files(work, patterns)])
        with tempfile.TemporaryDirectory(dir=workspace) as staging:
            staged = Path(staging) / name
            staged.mkdir()
            runbook = record / "README.md"
            if runbook.exists():
                os.link(runbook, staged / "README.md")
            else:
                (staged / "README.md").write_text(
                    f"# Local `{name}` run\n\nCohort `{cohort}`. Evidence workspace `{workspace.name}`.\n\n"
                    "Both trials used the canonical input in `input/`. Each trial has a separate working directory, "
                    "`first/` and `second/`, and its GNU time report is `time.txt`. "
                    "The profile specifies the commands and RDF paths relative to each trial directory.\n\n"
                    f"```toml\n{profile_text.rstrip()}\n```\n", encoding="utf-8")
            subprocess.run([sys.executable, "-B", ROOT / "benchmark.py", "record", "--submission", staged,
                            "--pipeline", name, "--cohort", cohort, "--input", workspace / "input", *recording],
                           check=True, timeout=86400)
            read_report(staged / "benchmark.json")
            if runbook.exists():
                os.link(staged / "benchmark.json", report)
            else:
                staged.rename(record)
    publish(build, record)
    print(f"Recorded {record}. Run make benchmarks to update the plots.")


def run_pipeline(name):
    profile_path = ROOT / "pipelines" / f"{slug(name)}.toml"
    profile_text = profile_path.read_text(encoding="utf-8")
    profile = tomllib.loads(profile_text)
    if unknown := set(profile) - {"command", "prepare", "rdf", "settings"}:
        raise ValueError(f"Unknown profile fields: {sorted(unknown)}")
    command = strings(profile, "command")
    prepare = strings(profile, "prepare") if "prepare" in profile else None
    strings(profile, "rdf")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f"{name}.", dir=build))
    print(f"Workspace: {workspace}", flush=True)
    profile_path = workspace / "profile.toml"
    profile_path.write_text(profile_text, encoding="utf-8")
    directory, archive = prepare_dataset(workspace)
    cohort = os.environ.get("MS2KG_COHORT")
    if not cohort:
        fingerprint = hashlib.sha256(Path("/etc/machine-id").read_bytes()).hexdigest()[:12]
        cohort = f"local-{fingerprint}"
    (workspace / "cohort.txt").write_text(slug(cohort) + "\n", encoding="utf-8")
    for label in ("first", "second"):
        work = workspace / label
        work.mkdir()
        environment = dict(os.environ, MS2KG_ROOT=str(ROOT), MS2KG_INPUT=str(directory), MS2KG_WORK=str(work),
                           MS2KG_CONFIG=str(profile_path), LC_ALL="C")
        if prepare:
            subprocess.run(prepare, cwd=ROOT, env={**environment, "MS2KG_ARCHIVE": str(archive)}, check=True, timeout=86400)
            verify_input(directory)
        timing = work / "time.txt"
        timed = ["/usr/bin/time", "-v", "-o", timing, "--"]
        print(f"Running {name} ({label})", flush=True)
        subprocess.run([*timed, *command], cwd=ROOT, env=environment, check=True, timeout=86400)
        verify_input(directory)
        if name in SHARED_READERS:
            export_trial(name, work, directory / "metadata/metadata.tsv")
            export_chemicals(name, work)
    recover(build, workspace, cohort)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("name", nargs="?")
    operation.add_argument("--recover", type=Path, metavar="WORKSPACE", help="publish completed evidence without running ETL")
    parser.add_argument("--cohort", help="original cohort for legacy evidence without a saved record")
    arguments = parser.parse_args()
    os.umask(0o077)
    try:
        if arguments.recover is not None:
            recover(ROOT / "build", arguments.recover, arguments.cohort)
        elif arguments.cohort is not None:
            parser.error("--cohort is only valid with --recover")
        else:
            run_pipeline(arguments.name)
    except (OSError, ValueError, BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(1, f"Pipeline failed: {error}\n")

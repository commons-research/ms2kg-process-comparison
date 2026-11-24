"""Select complete local record snapshots by an atomically replaced relative path."""

import os
import re
import tempfile
from pathlib import Path


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) or len(value) > 40:
        raise ValueError(f"Invalid slug {value!r}. Use up to 40 lowercase letters, digits and separating hyphens.")
    return value


def check_submission_directory(submission):
    slug(submission.name)
    if submission.is_symlink() or not submission.is_dir():
        raise ValueError(f"Expected a submission directory at {submission}")
    for entry in submission.iterdir():
        if entry.name not in {"README.md", "benchmark.json"} or entry.is_symlink() or not entry.is_file():
            raise ValueError(f"{entry}: submission directories may contain only README.md and benchmark.json")
    if not (submission / "README.md").is_file():
        raise ValueError(f"Missing runbook {submission / 'README.md'}")


def workspace_slug(directory):
    name, separator, identifier = directory.name.partition('.')
    if not separator or not re.fullmatch(r'[a-zA-Z0-9_-]+', identifier):
        raise ValueError(f'Invalid workspace name {directory.name!r}')
    return slug(name)


def checked_directory(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f'Expected a regular directory at {directory}')
    return directory


def snapshot(build, name, relative):
    parts = relative.split('/')
    if len(parts) != 3 or parts[1:] != ['record', name] or workspace_slug(Path(parts[0])) != name:
        raise ValueError(f'Invalid latest record path {relative!r} for {name}')
    directory = checked_directory(checked_directory(build) / parts[0])
    record = checked_directory(directory / 'record') / name
    check_submission_directory(record)
    if not (record / 'benchmark.json').is_file():
        raise ValueError(f'Missing benchmark.json in {record}')
    return record


def publish(build, record):
    relative = record.relative_to(build).as_posix()
    snapshot(build, record.name, relative)
    latest = build / 'latest'
    latest.mkdir(exist_ok=True)
    checked_directory(latest)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=build, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(relative + '\n')
            stream.flush()
            os.replace(temporary, latest / record.name)
        finally:
            temporary.unlink(missing_ok=True)


def local_records(build, legacy=None):
    latest = build / 'latest'
    legacy = build / 'records' if legacy is None else legacy
    selected = {}
    if latest.exists() or latest.is_symlink():
        for pointer in checked_directory(latest).iterdir():
            name = slug(pointer.name)
            if pointer.is_symlink() or not pointer.is_file():
                raise ValueError(f'Expected a regular pointer file at {pointer}')
            relative = pointer.read_text(encoding='utf-8').removesuffix('\n')
            selected[name] = snapshot(build, name, relative)
    if legacy.exists() or legacy.is_symlink():
        for record in checked_directory(legacy).iterdir():
            selected.setdefault(record.name, record)
    return [selected[name] for name in sorted(selected)]

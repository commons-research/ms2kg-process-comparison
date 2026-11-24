"""Install complete plot generations before switching the reader's Markdown index."""

import fcntl
import hashlib
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory


INDEX = "comparison.md"
GENERATION = re.compile(r"plots-[0-9a-f]{64}")
PLOT = re.compile(r"graph\.svg|timing-[a-z0-9]+(?:-[a-z0-9]+)*\.svg")


def generation_name(charts):
    digest = hashlib.sha256()
    for name, content in sorted(charts.items()):
        digest.update(name.encode("ascii") + b"\0" + hashlib.sha256(content).digest())
    return "plots-" + digest.hexdigest()


def require_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular report file at {path}")


def plot_files(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Expected a plot directory at {directory}")
    files = set(directory.iterdir())
    for path in files:
        if not PLOT.fullmatch(path.name):
            raise ValueError(f"Unrelated file in report directory: {path}")
        require_regular(path)
    return files


def managed_files(output):
    entries = set(output.iterdir())
    for path in list(entries):
        if GENERATION.fullmatch(path.name):
            entries.update(plot_files(path))
        elif path.name == INDEX:
            require_regular(path)
        else:
            raise ValueError(f"Unrelated entry in report directory: {path}")
    return entries


def store_comparison(output, generation, charts, markdown, *, published, check):
    if output.is_symlink():
        raise ValueError(f"Refusing a symbolic link as report directory: {output}")
    if not check:
        output.mkdir(parents=True, exist_ok=True)
    index = output / INDEX
    directory = output / generation
    descriptor = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, (fcntl.LOCK_SH if check else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        expected = {directory / name: data for name, data in charts.items()}
        expected[index] = markdown.encode("utf-8")
        if published:
            existing = managed_files(output)
        else:
            existing = set()
            if charts and (directory.exists() or directory.is_symlink()):
                files = plot_files(directory)
                if files != expected.keys() - {index}:
                    raise ValueError(f"Unexpected files in local plot directory: {directory}")
                existing = files | {directory}
            if index.exists() or index.is_symlink():
                require_regular(index)
                existing.add(index)

        obsolete = existing - expected.keys() - ({directory} if charts else set())
        changed = [path for path, data in expected.items() if path not in existing or path.read_bytes() != data]
        if not published and directory in existing and any(path != index for path in changed):
            raise ValueError(f"Unexpected contents in local plot directory: {directory}")
        if check:
            if changed or obsolete:
                paths = ", ".join(str(path) for path in sorted(set(changed) | obsolete))
                raise ValueError(f"Stale benchmark publication: {paths}")
            return
        if changed:
            with TemporaryDirectory(prefix=".benchmark-report-", dir=output.parent) as temporary:
                staging = Path(temporary)
                for path in changed:
                    staged = staging / path.relative_to(output)
                    staged.parent.mkdir(exist_ok=True)
                    staged.write_bytes(expected[path])
                if charts and directory not in existing:
                    os.replace(staging / generation, directory)
                else:
                    for path in changed:
                        if path != index:
                            os.replace(staging / path.relative_to(output), path)
                if index in changed:
                    os.replace(staging / INDEX, index)
        for path in sorted(obsolete, reverse=True):
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()
    finally:
        os.close(descriptor)

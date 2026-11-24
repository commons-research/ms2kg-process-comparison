"""Prepare and attest the exact source files shared by all ETL benchmarks."""

import argparse
import hashlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile


DATASET_SHA256 = "0c8bc4f8d350999a5b2910774e00cd4731ea32ffacbf2c0828258966583ed450"
INPUT_DIGESTS = {
    "metadata/metadata.tsv": "7aa006e47ea21ad3059529a5cebf5f7f876efe0dde0c00e74bf0378dd11e3fd0",
    "msdata/raw/VGF138_A01_neg.mzXML": "5f69c95992e56a30453bd5b7b8fb2f5b7013e438d87f8abe859721ebbcaf1ac3",
    "msdata/raw/VGF138_A01_pos.mzXML": "db7358b02f9099c3b8de012ed7c6a367e1c3d0edaed38d7f85ac2ddb1f82aaca",
    "msdata/raw/VGF140_H12_neg.mzXML": "50e3f0497f73495a390397d357c355202f72af73d154ac63a2f028a62c631ce0",
    "msdata/raw/VGF140_H12_pos.mzXML": "a4490e24574f9e954fcd5e5d4565d74d89760813d6d4193a5e0cdc2de58af29f",
    "msdata/raw/VGF151_E05_neg.mzXML": "6a4394cf9ed8f49aed6477d7802dc5bc2850e144c98c671cc785f814b7335ffc",
    "msdata/raw/VGF151_E05_pos.mzXML": "103433dc0528c16f6180f8bf029d2a16b60e8b505eb5b885e415e523c324f19b",
}


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_input(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Expected a raw input directory at {root}")
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_symlink() and path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if name not in INPUT_DIGESTS or path.is_symlink() or not path.is_file():
            raise ValueError(f"{root}: unexpected input entry {name}")
        files[name] = path
    for name, digest in INPUT_DIGESTS.items():
        if name not in files:
            raise ValueError(f"{root}: missing input file {name}")
        if sha256(files[name]) != digest:
            raise ValueError(f"{root}: checksum mismatch for {name}")


def prepare_input(archive, output):
    if sha256(archive) != DATASET_SHA256:
        raise ValueError("Archive SHA-256 does not match ENPKG toy release 0.2")
    output.mkdir()
    with ZipFile(archive) as dataset:
        for name in INPUT_DIGESTS:
            dataset.extract(name, output)
    verify_input(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="extract only the canonical raw inputs from the release ZIP")
    prepare.add_argument("archive", type=Path)
    prepare.add_argument("output", type=Path, help="new input directory")
    verify = commands.add_parser("verify", help="verify an existing raw input directory")
    verify.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare_input(args.archive, args.output)
            print(args.output)
        else:
            verify_input(args.input)
            print(args.input)
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(1, f"Input verification failed: {error}\n")


if __name__ == "__main__":
    main()

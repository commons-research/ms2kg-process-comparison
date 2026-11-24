"""Stage the pinned ENPKG benchmark without importing sample results or running ETL."""

import csv
import hashlib
import json
import os
import shutil
import subprocess
from importlib.metadata import version
from pathlib import Path
from zipfile import ZipFile

import tomllib
import yaml
from packaging.requirements import Requirement


REVISION = "a6535a5dfda9f4c59c79f39401359cb14c521a86"
TAXONOMY = "02_enpkg_taxo_enhancer/src/taxo_info_fetcher.py"
LOCAL_TAXONOMY_SHA256 = "deb7eca47dbeeba193578bae0c59b797f5042e84679de57e33994b8c8c41a8a5"
ISDB = Path("03_enpkg_mn_isdb_isdb_taxo")
REFERENCES = {
    "db_metadata/230106_frozen_metadata.csv.gz": "a206b62537733a3e8345598aacec7e8059ab777219d4b867003d49e692a65945",
    "db_spectra/isdb_pos_cleaned.pkl": "cb57b8aa96892e7a70278616295802fc35fee653ec5f32e2d329d59d3258cf0b",
}
METHOD_SHA256 = "a13c236180292e7f9b04262c54121e0873834f8beee0af0e5b934aa479d2d228"


def git(directory, *arguments):
    return subprocess.run(["git", "-C", directory, *arguments], check=True, stdout=subprocess.PIPE, timeout=120).stdout


def checkout(installed, trial):
    if git(installed, "rev-parse", "HEAD").decode().strip() != REVISION:
        raise SystemExit(f"Expected ENPKG at {REVISION} in {installed}")
    changes = git(installed, "diff", "--no-renames", "--name-only", REVISION, "--").decode().splitlines()
    if changes and changes != [TAXONOMY]:
        raise SystemExit(f"Unexpected tracked changes in ENPKG checkout: {changes}")
    trial.mkdir()
    git(trial, "clone", "--no-hardlinks", "--no-checkout", "--", str(installed), ".")
    git(trial, "checkout", "--detach", REVISION)
    if not changes:
        return {"kind": "clean upstream"}
    modified = (installed / TAXONOMY).read_bytes()
    if hashlib.sha256(modified).hexdigest() != LOCAL_TAXONOMY_SHA256:
        raise SystemExit(f"Unrecognized installed modification to {TAXONOMY}")
    (trial / TAXONOMY).write_bytes(modified)
    patch = trial.parent / "installed-taxonomy.patch"
    patch.write_bytes(git(trial, "diff", "--no-ext-diff", "--no-textconv", "--binary", REVISION, "--", TAXONOMY))
    return {"kind": "installed local modification", "path": TAXONOMY, "sha256": LOCAL_TAXONOMY_SHA256, "diff": patch.name}


def stage_references(installed, trial):
    for name, expected in REFERENCES.items():
        source = installed / ISDB / name
        if not source.is_file():
            raise SystemExit(f"Missing {source}. Provision ENPKG references using workflow/04_workflow_dl_ressources.sh in the external checkout.")
        destination = trial / ISDB / name
        destination.parent.mkdir(exist_ok=True)
        subprocess.run(["cp", "--reflink=auto", "--", source, destination], check=True, timeout=300)
        with destination.open("rb") as reference:
            if hashlib.file_digest(reference, "sha256").hexdigest() != expected:
                raise SystemExit(f"Unexpected ENPKG reference digest for {source}")


def configure(root, trial, sirius):
    config = trial / "params/user.yml"
    settings = yaml.safe_load(config.read_text())
    input_directory = trial / "data/input"
    dataset = input_directory / "enpkg_toy_dataset"
    metadata = dataset / "metadata"
    processed = dataset / "msdata/processed"
    metadata.mkdir(parents=True)
    processed.mkdir(parents=True)
    organization = settings["data-organization"]
    sample_metadata = metadata / organization["sample_metadata_filename"]
    shutil.copyfile(Path(os.environ["MS2KG_INPUT"]) / "metadata/metadata.tsv", sample_metadata)
    with sample_metadata.open(newline="") as source:
        accessions = {row["massive_id"] for row in csv.DictReader(source, delimiter="\t")}
    if accessions != {settings["massive-id-addition"]["massive_id"]}:
        raise SystemExit("Pinned MassIVE accession disagrees with canonical metadata")
    method_name = organization["lcms_method_params_filename"]
    with ZipFile(os.environ["MS2KG_ARCHIVE"]) as archive:
        method = archive.read(f"metadata/{method_name}")
    if hashlib.sha256(method).hexdigest() != METHOD_SHA256:
        raise SystemExit("Unexpected LCMS acquisition method in the toy archive")
    (metadata / method_name).write_bytes(method)
    batch = root / "legacy_enpkg/toy-unaligned.mzbatch"
    shutil.copyfile(batch, metadata / organization["lcms_processing_params_filename"])
    settings["sirius"]["paths"]["path_to_sirius"] = str(sirius)
    config.write_text(yaml.safe_dump(settings, sort_keys=False))


def main():
    root = Path(os.environ["MS2KG_ROOT"]).resolve(strict=True)
    installed = Path(os.environ["ENPKG_ROOT"])
    work = Path(os.environ["MS2KG_WORK"]).resolve(strict=True)
    if work.is_relative_to(installed):
        raise SystemExit("ENPKG trial must be outside the installed checkout")
    sirius = Path(os.environ.get("PATH_TO_SIRIUS", installed / "sirius-install/sirius/bin/sirius")).expanduser()
    if not sirius.is_absolute() or not sirius.is_file() or not os.access(sirius, os.X_OK):
        raise SystemExit("Set PATH_TO_SIRIUS to the absolute path of the SIRIUS 6 executable")
    trial = work / "enpkg"
    taxonomy = checkout(installed, trial)
    with (trial / "pyproject.toml").open("rb") as manifest:
        dependencies = tomllib.load(manifest)["project"]["dependencies"]
    for specification in dependencies:
        requirement = Requirement(specification)
        if version(requirement.name) not in requirement.specifier:
            raise SystemExit(f"ENPKG virtual environment does not satisfy {requirement}. Run uv sync --frozen in {installed}.")
    stage_references(installed, trial)
    configure(root, trial, sirius.resolve(strict=True))
    provenance = {"revision": REVISION, "taxonomy": taxonomy, "source_settings": "params/user.yml", "references_sha256": REFERENCES, "acquisition_method_sha256": METHOD_SHA256, "sirius": str(sirius), "venv": str(installed / ".venv")}
    (work / "enpkg-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance), flush=True)


if __name__ == "__main__":
    main()

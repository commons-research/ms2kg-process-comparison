"""Read the shared sample and acquisition facts from a finalized Flock database."""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path


_POLARITY = {"sample_filename_pos": "pos", "sample_filename_neg": "neg"}


def _read_samples(database):
    datasets = database.execute("SELECT id FROM datasets LIMIT 2").fetchall()
    if len(datasets) != 1 or not isinstance(datasets[0][0], int):
        raise ValueError("Expected exactly one Flock dataset with an integer ID")
    dataset_id = datasets[0][0]
    if database.execute("""
        SELECT 1 FROM taxon_resolutions
        WHERE NOT EXISTS (SELECT 1 FROM taxa WHERE taxa.id = taxon_resolutions.taxon_id)
        LIMIT 1
    """).fetchone():
        raise ValueError("Flock taxon resolution refers to a missing taxon")

    samples = {}
    for dataset, number, sample_id, attributes, taxon_id, taxon_name, qid in database.execute("""
        SELECT sample_rows.dataset_id, sample_rows.row_number, sample_rows.sample_id,
               sample_rows.attributes_json, sample_rows.taxon_id, taxa.name, taxon_resolutions.qid
        FROM sample_rows
        LEFT JOIN taxa ON taxa.id = sample_rows.taxon_id
        LEFT JOIN taxon_resolutions ON taxon_resolutions.taxon_id = taxa.id
        ORDER BY sample_rows.row_number
    """):
        key = (dataset, number)
        if dataset != dataset_id or not isinstance(number, int) or key in samples:
            raise ValueError(f"Invalid or ambiguous Flock sample row {key!r}")
        if not isinstance(sample_id, str) or not sample_id.strip() or not isinstance(attributes, str):
            raise ValueError(f"Invalid Flock sample identity or attributes at {key!r}")
        fields = json.loads(attributes)
        if not isinstance(fields, dict) or not isinstance(fields.get("source_taxon"), str):
            raise ValueError(f"Missing verbatim source taxon field for {sample_id}")
        role = fields.get("sample_type")
        if role not in ("sample", "qc", "blank"):
            raise ValueError(f"Invalid sample type for {sample_id}")
        verbatim = fields["source_taxon"]
        if taxon_id is not None and (not verbatim.strip() or taxon_name != verbatim.strip()):
            raise ValueError(f"Taxon link disagrees with the source taxon for {sample_id}")
        if qid is not None and (not isinstance(qid, str) or not re.fullmatch(r"Q[1-9][0-9]*", qid)):
            raise ValueError(f"Invalid taxon resolution for {sample_id}")
        samples[key] = (sample_id, role, verbatim, qid or "", [])

    for dataset, number, column, filename in database.execute("""
        SELECT dataset_id, row_number, column_name, filename
        FROM spectrum_files ORDER BY dataset_id, row_number, filename
    """):
        key = (dataset, number)
        if key not in samples:
            raise ValueError(f"Flock spectrum {filename!r} refers to missing sample row {key!r}")
        if column not in _POLARITY:
            raise ValueError(f"Unknown spectrum column {column!r} at {key!r}")
        if not isinstance(filename, str) or filename in ("", ".", "..") or Path(filename).name != filename:
            raise ValueError(f"Invalid spectrum filename {filename!r} at {key!r}")
        samples[key][4].append((_POLARITY[column], filename))
    return list(samples.values())


def read_samples(trial: Path) -> list[tuple[str, str, str, str, list[tuple[str, str]]]]:
    path = (trial / "flock" / "toy.sqlite").resolve(strict=True)
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as database:
            return _read_samples(database)
    except sqlite3.DatabaseError as error:
        code = getattr(error, "sqlite_errorcode", sqlite3.SQLITE_ERROR) & 0xFF
        if code in (sqlite3.SQLITE_ERROR, sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
            raise ValueError(f"Malformed Flock database at {path} ({error})") from error
        raise

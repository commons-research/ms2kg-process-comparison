"""Read ENPKG's individual sample records and MZmine's unaligned exports.

The per-sample metadata supplies roles, verbatim names and polarity assignments.
Each raw filename must also occur in its MZmine quantification table, including
negative acquisitions and controls. Taxon IDs come only from the sample's saved
resolution table, where ENPKG lowercases the query name.
"""

import csv
import re
from pathlib import Path


def _records(path, fields):
    with path.open(encoding="utf-8", newline="") as stream:
        try:
            reader = csv.DictReader(stream, delimiter="\t", strict=True)
            header = reader.fieldnames or []
            if any(header.count(field) != 1 for field in fields):
                raise ValueError(f"Invalid ENPKG columns in {path}")
            rows = list(reader)
        except csv.Error as error:
            raise ValueError(f"Malformed ENPKG table {path}") from error
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError(f"Missing or malformed ENPKG records in {path}")
    return rows


def _resolved_taxon(directory, name):
    path = directory / "taxo_output" / f"{directory.name}_taxo_metadata.tsv"
    if not name and not path.exists():
        return ""
    identifiers = set()
    for row in _records(path, ("sample_id", "source_taxon", "wd.value")):
        if not name or row["sample_id"] != directory.name or row["source_taxon"] != name.lower():
            raise ValueError(f"Taxon resolution does not match sample metadata in {path}")
        value = row["wd.value"]
        if value:
            match = re.fullmatch(r"https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)", value)
            if not match:
                raise ValueError(f"Invalid Wikidata entity {value!r} in {path}")
            identifiers.add(match[1])
    if len(identifiers) > 1:
        raise ValueError(f"Ambiguous Wikidata taxon in {path}")
    return next(iter(identifiers), "")


def _acquisition(output, filename):
    raw_file = Path(filename)
    if raw_file.name != filename or raw_file.suffix != ".mzXML":
        raise ValueError(f"Invalid ENPKG raw filename {filename!r}")
    path = output / raw_file.stem / f"{raw_file.stem}_iimn_fbmn_quant.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        try:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
        except csv.Error as error:
            raise ValueError(f"Malformed MZmine quantification table {path}") from error
    columns = [column for column in header if column.endswith(" Peak area")]
    if columns != [f"{filename} Peak area"]:
        raise ValueError(f"Missing or conflicting MZmine acquisition for {filename} in {path}")
    return columns[0].removesuffix(" Peak area")


def read_samples(trial: Path) -> list[tuple[str, str, str, str, list[tuple[str, str]]]]:
    """Read sample records and their independently evidenced acquisitions."""
    analysis = trial / "enpkg/data/output/individual_analysis"
    output = trial / "output"
    samples = []
    claimed = set()
    for directory in sorted(analysis.iterdir()):
        if not directory.is_dir():
            continue
        path = directory / f"{directory.name}_metadata.tsv"
        rows = _records(path, ("sample_id", "sample_type", "source_taxon", "sample_filename_pos", "sample_filename_neg"))
        if len(rows) != 1 or rows[0]["sample_id"] != directory.name:
            raise ValueError(f"Expected one sample matching its directory in {path}")
        row = rows[0]
        acquisitions = []
        for polarity in ("pos", "neg"):
            filename = _acquisition(output, row[f"sample_filename_{polarity}"])
            if filename in claimed:
                raise ValueError(f"MZmine acquisition {filename} claimed more than once in {analysis}")
            claimed.add(filename)
            acquisitions.append((polarity, filename))
        name = row["source_taxon"]
        samples.append((row["sample_id"], row["sample_type"], name, _resolved_taxon(directory, name), acquisitions))
    for directory in output.iterdir():
        if directory.is_dir() and f"{directory.name}.mzXML" not in claimed:
            raise ValueError(f"No ENPKG sample record for MZmine output {directory}")
    return samples

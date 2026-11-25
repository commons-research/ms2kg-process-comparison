# Isla Gabriola Flock

Run `make compare` from the comparison repository after provisioning both workflows. It runs the [native Mato job](job.toml) once in a fresh job directory using the same verified sample table and six raw spectra as ENPKG. Under `runs/run-*/flock/`, Mato writes the native graph to `flock/kg/graph-*.nq` and its report to `flock/reports/`.

## Workstation paths

| Variable | Default | Required contents |
| --- | --- | --- |
| `FLOCK_ROOT` | `flock/upstream/` in the comparison repository | Eight sibling source checkouts |
| `FLOCK_DATA_ROOT` | `/media/nvme8tb/isla-gabriola` | `hocofaisan/references/` and `mato/wikidata/` |

Use absolute overrides for installations elsewhere. Outside the timer, preparation checks tracked source revisions and modifications, verifies the [reference, settings and snapshot digests](references.sha256) and builds locked release binaries. The job directory retains the source and digest manifests. The timed command includes Mato's own Cargo freshness checks and run report. Keep shared references and checkouts unchanged during the run.

## Cold setup

Use Linux with Rust supporting edition 2024, Cargo, a C toolchain, `pkg-config`, and the OpenSSL and SQLite development libraries. The [source manifest](sources.lock) lists all eight repository URLs and full revision hashes. From the comparison repository root, provision a fresh installation with the following commands.

```bash
(
  set -eu
  installed=${FLOCK_ROOT:-"$PWD/flock/upstream"}
  mkdir -p "$installed"
  while read -r species revision upstream; do
    git clone "$upstream" "$installed/$species"
    git -C "$installed/$species" checkout --detach "$revision"
  done < flock/sources.lock
  git -C "$installed/hocofaisan" apply "$PWD/flock/hocofaisan.patch"
)
```

The [Hocofaisan patch](hocofaisan.patch) sets `feature_sources: None` in `SearchTaxonomyRequest` for the pinned spectral matcher. Preparation verifies the resulting `src/main.rs` against the SHA-256 in the digest manifest.

Under `$FLOCK_DATA_ROOT/hocofaisan/references/`, stage the [ISDB positive-mode library](https://zenodo.org/records/14887271/files/isdb_lotus_pos_energySum.mgf?download=1) as `isdb_lotus_pos_energySum.mgf` and decompress the [LOTUS metadata](https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1) to `230106_frozen_metadata.csv`. The job checks both uncompressed files and the matcher settings against the SHA-256 digests recorded by Hocofaisan for the toy annotation.

Under `$FLOCK_DATA_ROOT/mato/wikidata/`, stage the complete `taxa.sqlite` and `chemicals.sqlite` files identified in the [digest manifest](references.sha256). These snapshots are not bundled here. Cunaguaro's `taxon-index` and `chemical-index` commands query live Wikidata, so newly generated indexes cannot be assumed to match these files. `make compare` requires the exact snapshot bytes.

## Graph scope and checks

Mato validates and ingests the dataset, enriches taxa, processes both polarities with Picoto `jobs = 2`, registers outputs, annotates eligible spectra, enriches chemicals and exports N-Quads. The job uses dataset concept DOI `10.5281/zenodo.10018264` and disables index creation and partial graph export. [Hocofaisan](https://github.com/oolonek/hocofaisan/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/src/main.rs) skips blanks, quality controls and negative mode. Only the positive-mode biological sample qualifies for annotation.

The [Mato runner](https://github.com/oolonek/mato/blob/fc449d1ff4207ce07d4bef2120d2b2bd50cc1037/src/main.rs) requires populated index snapshots and the three Picoto output files for each raw spectrum. A failed annotation can leave saved hits available to chemical enrichment, but this profile suppresses partial graph export. After native export, the comparison runner writes `reconciled.ttl` in the Flock trial directory and validates it against the common [shapes](../schema/shapes-v2.ttl) outside the timer.

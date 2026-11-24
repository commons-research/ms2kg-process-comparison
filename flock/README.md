# Isla Gabriola Flock

Run `make pipeline flock` from the comparison repository. The [profile](../pipelines/flock.toml) runs the [native Mato job](job.toml) twice. Each trial starts with the verified metadata and six raw spectra, an empty job directory, and no database, processed spectra or annotations. The graph is `flock/kg/graph-*.nq` in the trial directory. Mato writes its report under `flock/reports/`.

## Workstation paths

| Variable | Default | Required contents |
| --- | --- | --- |
| `FLOCK_ROOT` | `$HOME/git_repos/oolonek/isla-gabriola-flock` | Sibling source checkouts listed below |
| `FLOCK_DATA_ROOT` | `/media/nvme8tb/isla-gabriola` | `hocofaisan/references/` and `mato/wikidata/` |

Set these variables only if the installation lives elsewhere. Preparation links the verified input and reference directories into the new job, verifies the annotation [checksums](references.sha256), records both Wikidata snapshot hashes in `wikidata.sha256`, and prebuilds the locked release binaries. The timed command includes Mato's own Cargo freshness checks and run report. Leave shared references and source checkouts unchanged throughout both trials.

## Cold setup

Use Linux with Rust supporting edition 2024, Cargo, a C toolchain, `pkg-config`, and the OpenSSL and SQLite development libraries. Check out these revisions as siblings under `FLOCK_ROOT` and retain their lockfiles.

| Repository | Revision |
| --- | --- |
| [Mato](https://github.com/oolonek/mato/commit/fc449d1ff4207ce07d4bef2120d2b2bd50cc1037) | `fc449d1` |
| [Sapayoa](https://github.com/oolonek/sapayoa/commit/666c50cecdff27ff3184abc1755bd002b531c560) | `666c50c` |
| [Machaca](https://github.com/oolonek/machaca/commit/47721b938685723f978320d676730020ecf893f5) | `47721b9` |
| [Peregrino](https://github.com/oolonek/peregrino/commit/765870d3a0ba80a7542453213d360b30e9cd4654) | `765870d` |
| [Cunaguaro](https://github.com/oolonek/cunaguaro/commit/82fa6eb0a97d55218a72e5c6f766fe568e9a611c) | `82fa6eb` |
| [Picoto](https://github.com/oolonek/picoto/commit/d3a89884b65240c3edf356dde76bdb2a26bbe875) | `d3a8988` |
| [Hocofaisan](https://github.com/oolonek/hocofaisan/commit/1d779f55165b1b227e16ebe126ec2675c47203c8) | `1d779f5` plus the local compatibility patch |
| [spectral-matcher](https://github.com/earth-metabolome-initiative/spectral-matcher/commit/01a169d00d86088f0de35cbd1975ce197cd20797) | `01a169d` |

**Public-source build blocker.** The pinned Hocofaisan and matcher revisions fail together with `E0063`. The workstation checkout adds `feature_sources: None` to `SearchTaxonomyRequest` in `search_file`. A clean public-source run needs a published compatible revision. The [workstation baseline runbook](../submissions/flock-workstation/README.md) describes the measured installation and its limits.

Under `$FLOCK_DATA_ROOT/hocofaisan/references/`, stage the [ISDB positive-mode library](https://zenodo.org/records/14887271/files/isdb_lotus_pos_energySum.mgf?download=1) as `isdb_lotus_pos_energySum.mgf` and decompress the [LOTUS metadata](https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1) to `230106_frozen_metadata.csv`. The job checks both uncompressed files and the matcher settings against the SHA-256 digests recorded by Hocofaisan for the toy annotation.

Under `$FLOCK_DATA_ROOT/mato/wikidata/`, stage complete `taxa.sqlite` and `chemicals.sqlite` snapshots from the same source as the comparison cohort. To generate new snapshots, create this directory and build Cunaguaro with `cargo build --locked --release --manifest-path "$FLOCK_ROOT/cunaguaro/Cargo.toml"`. Run its `taxon-index --index "$FLOCK_DATA_ROOT/mato/wikidata/taxa.sqlite"` and `chemical-index --index "$FLOCK_DATA_ROOT/mato/wikidata/chemicals.sqlite"` commands before benchmarking. These require network access and reflect the Wikidata endpoint at retrieval time. Reproducing an existing snapshot requires the matching files. Do not refresh an index during a trial.

## Graph scope and checks

Mato validates and ingests the dataset, enriches taxa, processes both polarities, registers Picoto outputs, annotates eligible spectra, enriches chemicals and exports N-Quads. [Hocofaisan](https://github.com/oolonek/hocofaisan/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/src/main.rs) intentionally skips blanks, quality controls and negative mode. The toy input therefore has one eligible positive-mode biological sample.

The [Mato runner](https://github.com/oolonek/mato/blob/fc449d1ff4207ce07d4bef2120d2b2bd50cc1037/src/main.rs) requires populated index snapshots and the three Picoto output files for each raw spectrum. Missing prerequisites fail the job. Per-file annotation errors allow chemical enrichment of saved hits, then suppress graph export and return a failing status with this profile. SHACL validation is outside the timer. Run `peregrino kg validate --graph <graph.nq>` on each emitted graph before submitting results.

# Flock workstation baseline

The [measured record](benchmark.json) contains two raw-to-RDF trials for `flock` in the same `workstation-raw-to-rdf` cohort as the [ENPKG baseline](../enpkg-workstation/README.md). The cohort uses a public machine alias.

| Trial | Wall time (s) | Peak RSS (KiB) | Distinct triples |
|---|---:|---:|---:|
| First | 25.63 | 12,648,408 | 152,265 |
| Second | 26.26 | 12,643,660 | 152,265 |

Each N-Quads export contains 152,265 distinct statements in the default graph, with 16 classes, 56 predicates and no blank nodes. The graphs are unequal despite the matching counts. Comparing the retained N-Quads lines as sets found one statement unique to each trial, both with predicate `urn:mato:term:createdAt`. The two Mato run reports each record three ingested sample records, six registered spectra, one hit file, 4,452 annotation hits and zero outstanding failed files. Hits are candidates, not independent confirmations of compound identity.

## Inputs and scientific scope

The [ENPKG toy release 0.2](https://doi.org/10.5281/zenodo.10018590) ZIP has SHA-256 `0c8bc4f8d350999a5b2910774e00cd4731ea32ffacbf2c0828258966583ed450`. The [job configuration](../../flock/job.toml) uses the dataset concept DOI `10.5281/zenodo.10018264`. The record hashes the sample table and all six raw `mzXML` files. Picoto processes both polarities for the biological sample `VGF151_E05`, QC `VGF138_A01` and blank `VGF140_H12`, with `jobs = 2`. Hocofaisan skips negative mode, blanks and QCs when annotating. Only the positive biological acquisition qualifies. Mato exports acquisition and processing provenance, features, query and reference spectra, candidate hits and supporting LOTUS matches. ENPKG exports a different scientific model, so the relative triple counts are not a measure of annotation quality.

Use the [Flock setup instructions and exact source revisions](../../flock/README.md#cold-setup) to provision the sibling Cargo checkouts. The shared checkout heads available through the retained workspace matched the following pins when inspected. The run reports do not freeze each source tree or the compiled binaries.

| Source | Revision |
|---|---|
| [Mato](https://github.com/oolonek/mato/commit/fc449d1ff4207ce07d4bef2120d2b2bd50cc1037) | `fc449d1ff4207ce07d4bef2120d2b2bd50cc1037` |
| [Sapayoa](https://github.com/oolonek/sapayoa/commit/666c50cecdff27ff3184abc1755bd002b531c560) | `666c50cecdff27ff3184abc1755bd002b531c560` |
| [Machaca](https://github.com/oolonek/machaca/commit/47721b938685723f978320d676730020ecf893f5) | `47721b938685723f978320d676730020ecf893f5` |
| [Peregrino](https://github.com/oolonek/peregrino/commit/765870d3a0ba80a7542453213d360b30e9cd4654) | `765870d3a0ba80a7542453213d360b30e9cd4654` |
| [Cunaguaro](https://github.com/oolonek/cunaguaro/commit/82fa6eb0a97d55218a72e5c6f766fe568e9a611c) | `82fa6eb0a97d55218a72e5c6f766fe568e9a611c` |
| [Picoto](https://github.com/oolonek/picoto/commit/d3a89884b65240c3edf356dde76bdb2a26bbe875) | `d3a89884b65240c3edf356dde76bdb2a26bbe875` |
| [Hocofaisan](https://github.com/oolonek/hocofaisan/commit/1d779f55165b1b227e16ebe126ec2675c47203c8) | `1d779f55165b1b227e16ebe126ec2675c47203c8` plus a local edit |
| [spectral-matcher](https://github.com/earth-metabolome-initiative/spectral-matcher/commit/01a169d00d86088f0de35cbd1975ce197cd20797) | `01a169d00d86088f0de35cbd1975ce197cd20797` |

The inspected Hocofaisan checkout adds `feature_sources: None` in the `SearchTaxonomyRequest` initializer in `search_file`. Its resulting `src/main.rs` has SHA-256 `e56478039ed306e92353f13db2c760a6e179a0f05843c69f8c266698ff3becc5`. The [Flock setup guide](../../flock/README.md#cold-setup) explains why the public pins alone cannot build this installation. The preparation step uses locked release builds. Exact compiler and system-library versions, executable hashes, a runner revision and a container image digest were not recorded. The benchmark did not capture a machine manifest with CPU model, RAM, OS/kernel, resource limits, background load or GNU `time` version. The paired ENPKG logs report 32 cores and 64 threads on this cohort. Flock has no independent hardware inventory in its trial reports.

| Reference | SHA-256 of bytes used |
|---|---|
| [Positive ISDB library](https://zenodo.org/records/14887271/files/isdb_lotus_pos_energySum.mgf?download=1) | `9ee96a1c2e337dc8c6a742e89b8065299260005c9520d85b2b71127d4f958933` |
| [LOTUS metadata](https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1), decompressed | `f08f5f3860a87987a7e8cffefbc1a72c70006a8ca1d4fccf8c28c4d61f7922e9` |
| Hocofaisan `config/example.toml` | `3de1c4a1acb0695117e6e7ce256cfd7b7a75d1671db59148c6a2b826082ae7d6` |
| Wikidata `taxa.sqlite` | `6b18d83a14239cf338e9ba571d41e8be8f9e1f47ec9b5f634b1c68cc43b2f9f3` |
| Wikidata `chemicals.sqlite` | `41921fe94dab80d4d22261e96459e8d4c9c83f65861119d18e65dc4dbf5c5f84` |

Both trial manifests identify the same Wikidata snapshots. These files and the other three references matched the recorded hashes on inspection. The SQL indexes are unpublished here. Generating new indexes queries live Wikidata and cannot guarantee these bytes. Exact replay of the scientific inputs requires the matching snapshots.

## Fresh run and limits

From the comparison repository root on a provisioned machine, run `MS2KG_COHORT=my-lab make pipeline flock`. Use a cohort alias for that machine and resource policy. The [profile](../../pipelines/flock.toml) prepares each trial with `bash flock/launch.sh prepare` outside the timer, then times `bash flock/launch.sh run` from the repository root using GNU `time -v`. Each of the two trials starts with a fresh job directory and database. Shared inputs, reference files, release binaries and operating-system caches can persist between trials. No cold-cache condition was recorded. The timed Mato stages validate and ingest the input, enrich taxa, process and register spectra, annotate, enrich chemicals and export RDF with partial export disabled. The recorder parses the two N-Quads outputs and tests dataset equivalence after timing.

Both Mato reports say `SHACL validated: no`. For a separate conformance check, run `peregrino kg validate --graph "$graph"` outside the timer with `graph` set to each trial's N-Quads path. This baseline does not certify an independently saved SHACL result.

## Evidence and replay

The [record](benchmark.json) is sufficient for `make results` to render this baseline without ETL. The retained local workspace is `build/flock.ecjbhcxk`. Both `first/` and `second/` contain `time.txt`, `flock/job.toml`, `flock/wikidata.sha256` and `flock/reports/run-*.md`. The exports are `first/flock/kg/graph-uyotRT.nq` and `second/flock/kg/graph-FZOLQY.nq`. The archive, seven extracted inputs, both timing reports and both RDF byte lengths and hashes were checked against the retained files. Both timing reports record exit status zero. No public evidence bundle or access grant is supplied. Raw reports, graphs, databases and snapshot files remain unpublished.

With access to the retained workspace, replay the record without running either pipeline. From the repository root with the comparison dependencies installed, run the following in Bash. It writes only to a new scratch submission and compares the complete decoded records.

```bash
set -eu
work=build/flock.ecjbhcxk
scratch=$(mktemp -d build/replay.XXXXXXXX)
submission=$scratch/flock-workstation
mkdir "$submission"
cp submissions/flock-workstation/README.md "$submission/"
.venv/bin/python benchmark.py record --submission "$submission" \
  --pipeline flock --cohort workstation-raw-to-rdf --input "$work/input" \
  --first-time "$work/first/time.txt" --first-rdf "$work/first/flock/kg/graph-uyotRT.nq" \
  --second-time "$work/second/time.txt" --second-rdf "$work/second/flock/kg/graph-FZOLQY.nq"
.venv/bin/python -c 'import json,sys; a,b=map(lambda path: json.load(open(path)),sys.argv[1:]); sys.exit(a != b)' \
  "$submission/benchmark.json" submissions/flock-workstation/benchmark.json
```

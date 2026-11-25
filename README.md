# Comparing MS-to-KG pipelines

[![Shared graph comparison](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/comparison.yml/badge.svg)](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/comparison.yml)

**[Common schema](schema/shapes-v2.ttl) · [Mapping and validation guide](schema/README.md) · [Taxon–chemical pair query](rdf/taxon-chemical-pairs.rq)**

ENPKG and Isla Gabriola Flock each process the same six raw acquisitions and sample metadata from [ENPKG toy dataset 0.2](https://doi.org/10.5281/zenodo.10018590). Each retains its native RDF. The two adapters map the native evidence into separate Turtle graphs that conform to the same tracked SHACL shapes. The [toy fixture](fixtures/toy-v2.ttl) gives expected sample facts for this dataset only.

## Run from scratch

On Linux, install GNU Make, GNU `time`, `uv` and Python 3.11 or later. Provision [ENPKG with MZmine and SIRIUS](legacy_enpkg/README.md) and [Flock with its pinned references](flock/README.md). From the repository root run:

```bash
make compare
```

Each invocation creates a private `runs/run-*/` directory and runs each pipeline **once**. No previous trial is reused or overwritten. ENPKG uses [`for-benchmark` at `53aff82d01`](https://github.com/enpkg/enpkg_full/tree/53aff82d01be6856cfd12a9910ddb9fff93dc0bd). Flock uses the [pinned source revisions](flock/sources.lock) and [Mato job](flock/job.toml).

| Inside the printed run directory | What to inspect |
|---|---|
| `comparison.tsv` | Wall seconds and peak resident memory in KiB for native ETL and reconciliation separately, plus distinct triple counts for each graph |
| `enpkg/native.sha256`, `flock/native.sha256` | Relative filenames and checksums of the original Turtle or N-Quads exports under each pipeline directory |
| `enpkg/reconciled.ttl`, `flock/reconciled.ttl` | Each pipeline’s annotations expressed under the common schema |
| `pair-summary.md`, `pair-evidence.tsv` | Shared and exclusive Wikidata taxon–chemical pairs, including annotation method and key agreement |

Native counts take the union across documents and named graphs. Reconciliation represents the evidence covered by the common schema, so its triple count can be larger or smaller than the native count. The timers exclude setup, counting, SHACL validation and comparison. A single measurement describes this run. It cannot establish timing variability or confirm that a proposed chemical occurs in the sample.

[Change the schema or an adapter](CONTRIBUTING.md). Keep raw logs, credentials, generated graphs and measurements out of Git.

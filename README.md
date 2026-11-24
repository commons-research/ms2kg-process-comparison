# Comparing MS-to-KG ETL pipelines

[![Benchmark](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/benchmark.yml/badge.svg)](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/benchmark.yml)

The benchmark has compared [ENPKG and Isla Gabriola Flock](results/comparison.md) on the same raw data. [Submissions from additional pipelines are welcome](CONTRIBUTING.md).

**[Download the four shared RDF graphs](rdf/README.md)** or [compare the Wikidata taxon–chemical pairs by annotation method](rdf/pair-summary.md). The [row-level evidence](rdf/pair-evidence.tsv) identifies the trial, pipeline, software and procedure behind each proposed association.

Both pipelines start with the same six raw spectra and sample metadata from [ENPKG toy dataset 0.2](https://doi.org/10.5281/zenodo.10018590). The runbooks for [ENPKG with chemical Wikidata enrichment](submissions/enpkg-53aff82-workstation/README.md), the [original ENPKG baseline](submissions/enpkg-workstation/README.md) and [Flock](submissions/flock-workstation/README.md) explain which annotations contribute to each graph and how the trials were measured.

## Run a comparison

Use Linux, GNU Make and Python 3.11 or later. Follow the setup guide for [ENPKG including MZmine](legacy_enpkg/README.md) or [Isla Gabriola Flock](flock/README.md), then run from the repository root.

```sh
make pipeline enpkg
make pipeline flock
make benchmarks
```

Each pipeline command measures two fresh raw-to-RDF runs. `make benchmarks` builds a private preview at `build/comparison.md` from saved results without launching a pipeline.

**[Contribute a pipeline or a result](CONTRIBUTING.md)** with a runnable profile, a measured record and a runbook.

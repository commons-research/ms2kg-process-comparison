# Comparing MS-to-KG ETL pipelines

[![Benchmark](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/benchmark.yml/badge.svg)](https://github.com/commons-research/ms2kg-process-comparison/actions/workflows/benchmark.yml)

**[View the ENPKG and Isla Gabriola Flock comparison](results/comparison.md)** for execution time, peak memory, graph characteristics and RDF repeatability. The report includes both trials of each pipeline. No installation is needed to read it.

Both pipelines start with the same six raw spectra and sample metadata from [ENPKG toy dataset 0.2](https://doi.org/10.5281/zenodo.10018590). Triple counts describe graph size. The [ENPKG](submissions/enpkg-workstation/README.md) and [Flock](submissions/flock-workstation/README.md) runbooks explain annotation scope, local source changes and what another lab can reproduce.

## Run a comparison

Use Linux, GNU Make and Python 3.11 or later. Follow the setup guide for [ENPKG including MZmine](legacy_enpkg/README.md) or [Isla Gabriola Flock](flock/README.md), then run from the repository root.

```sh
make pipeline enpkg
make pipeline flock
make benchmarks
```

Each pipeline command measures two fresh raw-to-RDF runs. `make benchmarks` builds a private preview at `build/comparison.md` from saved results without launching a pipeline.

**[Contribute a pipeline or a result](CONTRIBUTING.md)** with a runnable profile, a measured record and a runbook.

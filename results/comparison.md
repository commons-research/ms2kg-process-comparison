# ENPKG toy benchmark comparison

Each record contains two raw-to-RDF runs on the same canonical input. RDF equivalence compares the two outputs within a record.

| Record | Source | RDF equivalence of runs 1 and 2 | Evidence |
| --- | --- | --- | --- |
| enpkg-53aff82-workstation | Submitted | non-equivalent | [Runbook](../submissions/enpkg-53aff82-workstation/README.md) · [Record](../submissions/enpkg-53aff82-workstation/benchmark.json) |
| enpkg-workstation | Submitted | non-equivalent | [Runbook](../submissions/enpkg-workstation/README.md) · [Record](../submissions/enpkg-workstation/benchmark.json) |
| flock-workstation | Submitted | non-equivalent | [Runbook](../submissions/flock-workstation/README.md) · [Record](../submissions/flock-workstation/benchmark.json) |

## Raw-to-RDF timing

Compare individual runs within the same declared machine and protocol cohort. Each panel has its own scale.

### workstation-raw-to-rdf

![Wall time and peak memory for workstation-raw-to-rdf](plots-13e5a7e15be2a397991c39a0e59bba7d9e807fb5c3ded1a30b7bd5c0e4707d0b/timing-workstation-raw-to-rdf.svg)

## RDF output characteristics

The runbooks describe each pipeline's graph scope. Counts alone do not establish equivalent coverage.

![RDF output characteristics by run](plots-13e5a7e15be2a397991c39a0e59bba7d9e807fb5c3ded1a30b7bd5c0e4707d0b/graph.svg)

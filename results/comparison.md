# ENPKG toy benchmark comparison

Each record contains two raw-to-RDF runs on the same canonical input. RDF equivalence compares the two outputs within a record.

| Record | Source | RDF equivalence of runs 1 and 2 | Evidence |
| --- | --- | --- | --- |
| enpkg-workstation | Submitted | non-equivalent | [Runbook](../submissions/enpkg-workstation/README.md) · [Record](../submissions/enpkg-workstation/benchmark.json) |
| flock-workstation | Submitted | non-equivalent | [Runbook](../submissions/flock-workstation/README.md) · [Record](../submissions/flock-workstation/benchmark.json) |

## Raw-to-RDF timing

Compare individual runs within the same declared machine and protocol cohort. Each panel has its own scale.

### workstation-raw-to-rdf

![Wall time and peak memory for workstation-raw-to-rdf](plots-a6b45e297125ba8342d43a9095fc91ccccb4b1096ccbf0107a508bf5a307f4f3/timing-workstation-raw-to-rdf.svg)

## RDF output characteristics

The runbooks describe each pipeline's graph scope. Counts alone do not establish equivalent coverage.

![RDF output characteristics by run](plots-a6b45e297125ba8342d43a9095fc91ccccb4b1096ccbf0107a508bf5a307f4f3/graph.svg)

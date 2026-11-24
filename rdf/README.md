# Shared RDF trial graphs

Each download contains the full [version 2 application profile](../schema/README.md) for one trial. The material and acquisition records join to the chemical annotations through the raw file IRI. Keep each trial in a separate graph when comparing results. The [query example](../schema/README.md#query-both-exports) reads a download directly, without either pipeline or a Wikidata connection.

| Pipeline and trial | SHA-256 of the `.ttl.gz` download |
|---|---|
| [ENPKG first](enpkg-first.ttl.gz) | `48ce6687c789b27e4c29e05a870528ff3b95889af1aedfd95ebdce8c405adaac` |
| [ENPKG second](enpkg-second.ttl.gz) | `9357dd4a00fa0b24fba0d3fc7b42a7a3e5d0539570ff28a97501b6937834106e` |
| [Flock first](flock-first.ttl.gz) | `f760a55075f20c5d3df8d70720519e6c5e073255dc4187da70aa31ecd189ba11` |
| [Flock second](flock-second.ttl.gz) | `b1715f24bf521e45f8c653798b4705ede9d70b3eb1870a691d263031f041ffaf` |

Run `sha256sum rdf/*.ttl.gz` from the repository root to compare a checkout with these digests. To write plain Turtle, run `gzip -dc rdf/enpkg-first.ttl.gz > enpkg-first.ttl`.

## Which taxon–chemical pairs do the workflows share?

Open the [overlap by trial and annotation method](pair-summary.md) or download the [pair-level evidence](pair-evidence.tsv). Run `make pairs` to recompute both from the four downloads without service credentials or native ETL workspaces. The [SPARQL query](taxon-chemical-pairs.rq) follows the source identification through the biological sample and its acquisition to the feature, candidate and Wikidata reference. Each pipeline and trial is queried separately.

For example, both workflows propose [Q103818563](https://www.wikidata.org/wiki/Q103818563) for [*Datura stramonium*](https://www.wikidata.org/wiki/Q30959) in trial 1. ENPKG's SIRIUS candidate supplies connectivity block `DNVPQKQSNYMLRS`. Flock's library candidate and its reference share the full key `DNVPQKQSNYMLRS-UHFFFAOYSA-N`. Agreement on the Wikidata pair does not imply the same method, the same feature or equal structural specificity.

## Source records

Both pipelines used [ENPKG toy dataset release 0.2](https://doi.org/10.5281/zenodo.10018590), with two acquisitions each for one biological extract, one QC and one blank. The extract is labelled *Datura stramonium* ([Q30959](https://www.wikidata.org/wiki/Q30959)). Chemical candidates concern its positive-mode acquisition. A candidate linked to a Wikidata item records an annotation and its reference evidence. Connectivity-block matches can associate several stereoisomers with one candidate. These data do not confirm the presence of a particular compound in the plant.

- **ENPKG** used [revision `53aff82d01`](https://github.com/enpkg/enpkg_full/tree/53aff82d01be6856cfd12a9910ddb9fff93dc0bd). The [trial record](../submissions/enpkg-53aff82-workstation/benchmark.json) identifies the inputs and native exports. The [measurement notes](../submissions/enpkg-53aff82-workstation/README.md) describe live service and taxonomy dependencies. The [chemical adapter](../legacy_enpkg/chemicals.py) reads the final SIRIUS and reweighted ISDB reports and associated structure references.
- **Isla Gabriola Flock** used the revisions and reference snapshots in the [measurement notes](../submissions/flock-workstation/README.md). The [trial record](../submissions/flock-workstation/benchmark.json) identifies the inputs and native exports. The [chemical adapter](../flock/chemicals.py) reads saved hits, chemical-index records and LOTUS structures.

The hashes in the measurement records describe the native exports. The hashes above describe the derived graphs. Native databases, service responses and run logs are outside this release.

## Regenerate from a completed pair of workspaces

With both native trial workspaces and their verified input directories available, run the following in Bash from the repository root. The commands write new downloads under `build/`. For fresh measurements, follow the linked pipeline-specific measurement notes, including the ENPKG revision pin and the Flock snapshot limitations.

```bash
set -euo pipefail
enpkg=build/enpkg-rerun-53aff82d01/runner/build/enpkg.i9ncucs_
flock=build/flock.ecjbhcxk
make shared ENPKG="$enpkg" FLOCK="$flock"
output=$(mktemp -d build/rdf-export.XXXXXXXX)
for pipeline in enpkg flock; do
    workspace=${!pipeline}
    for trial in first second; do
        cat "$workspace/$trial/shared-v2.ttl" "$workspace/$trial/chemicals-v2.ttl" |
            gzip -n -9 > "$output/$pipeline-$trial.ttl.gz"
    done
done
printf '%s\n' "$output"
```

Packaging the retained Turtle bytes in this order preserves the full trial export. A fresh RDF serialization can change blank-node labels and statement order. Compare regenerated RDF graphs by isomorphism, and use the download hashes to check exact file identity.

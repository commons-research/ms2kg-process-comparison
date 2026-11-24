# Shared RDF application profile, version 2

Each trial exports two Turtle files. `shared-v2.ttl` describes the materials, acquisitions, raw files and reported source taxon. `chemicals-v2.ttl` describes candidate structures, the features they annotate and the evidence for their Wikidata associations. The two graphs join through the raw file IRI. The benchmark assigns identifiers to its data and uses external vocabularies to describe them.

## Generate and compare

The [published trial graphs](../rdf/README.md) can be queried without running either pipeline. After running both benchmark profiles, use `make shared` from the repository root to compare the latest local workspaces. With access to the retained [ENPKG `53aff82d01`](../submissions/enpkg-53aff82-workstation/README.md#measurement-and-reproduction) and [Flock](../submissions/flock-workstation/README.md#evidence-and-replay) workspaces, select them explicitly.

```bash
make shared ENPKG=build/enpkg-rerun-53aff82d01/runner/build/enpkg.i9ncucs_ FLOCK=build/flock.ecjbhcxk
```

Open `first/shared-v2.ttl` and `first/chemicals-v2.ttl` under either workspace. `second/` contains the independent second trial. Replay reads the verified source manifest and the trial's native records. No ETL, live Wikidata query or service credential is needed. The public measurement summaries alone cannot reconstruct these files. New pipeline runs generate both shared files outside the native raw-to-RDF timer.

**Two different comparisons.** The sample graphs must match each other and the [independently specified toy graph](toy-v2.ttl). The candidate inventories may differ. `make shared` reports missing or extra sample triples, native candidate counts, the number with Wikidata associations, and distinct identifiers present on both sides or only one side. Shared chemical connectivity does not establish that the same chromatographic peak was annotated. Multiple hits may refer to one chemical, and multiple Wikidata items may share a full InChIKey.

## Sample and acquisition facts

Each material has a release-scoped IRI, a [`dcterms:identifier`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/identifier/) and the verbatim role (`sample`, `qc` or `blank`) as `dcterms:type`. Only the biological extract is typed [`sosa:Sample`](https://www.w3.org/TR/2017/REC-vocab-ssn-20171019/#SOSASample). The extract `prov:wasDerivedFrom` a source material. A [Darwin Core identification](https://dwc.tdwg.org/rdf/#274-description-of-a-taxonomic-entity-normative) about that source retains `dwc:verbatimIdentification` even when resolution fails. Only a resolved taxon has `dwciri:toTaxon` pointing to its Wikidata item. No taxon or biological parent is supplied for the blank or QC.

An [LC-MS assay](http://purl.obolibrary.org/obo/OBI_0003097) is a `prov:Activity` that `prov:used` the material. `dcterms:relation` links it to the raw `schema:MediaObject`, with its filename in `schema:name` and its verified digest in [`schema:sha256`](https://schema.org/sha256). This association leaves open which conversion software produced the actual bytes. The more general Wikidata [checksum property](https://www.wikidata.org/wiki/Property:P4092) needs an additional qualifier to convey the algorithm. `sio:SIO_000008` associates the assay with a scan-polarity attribute typed with the PSI-MS [positive](http://purl.obolibrary.org/obo/MS_1000130) or [negative](http://purl.obolibrary.org/obo/MS_1000129) term. This profile describes the toy release's single-polarity files.

## Chemical observations

A computational [`sosa:Observation`](https://www.w3.org/TR/2017/REC-vocab-ssn-20171019/#SOSAObservation) studies the [chemical structure](https://www.wikidata.org/wiki/Q500256) associated with a producer-local feature. Its `sosa:hasResult` is a candidate description. Its `sosa:usedProcedure` distinguishes database search, de novo prediction, spectral matching, analogue search and the other native annotation methods. `prov:used` identifies the actual software, including [SIRIUS](https://www.wikidata.org/wiki/Q124358188). SIRIUS [documents its distinct workflows](https://v6.docs.sirius-ms.io/methods-background/). An analogue result describes the reference analogue. No result asserts the presence of a confirmed compound in a sample.

| Evidence | Representation |
|---|---|
| Source SMILES with unspecified flavor | [`schema:smiles`](https://schema.org/smiles), preserving the input string. Do not claim [canonical SMILES](https://www.wikidata.org/wiki/Property:P233) without a source establishing canonicalization. |
| Sourced isomeric SMILES on a reference record | [`wdt:P2017`](https://www.wikidata.org/wiki/Property:P2017). A generic fallback for a missing isomeric value does not qualify. |
| InChI, full InChIKey, neutral formula, PubChem CID | Wikidata direct properties [`P234`](https://www.wikidata.org/wiki/Property:P234), [`P235`](https://www.wikidata.org/wiki/Property:P235), [`P274`](https://www.wikidata.org/wiki/Property:P274) and [`P662`](https://www.wikidata.org/wiki/Property:P662) on the description that supplied the value. |
| 14-character InChIKey connectivity block | `schema:identifier` points to a [`schema:PropertyValue`](https://schema.org/PropertyValue) with `schema:propertyID "InChIKey connectivity block"` and the original `schema:value`. A short block cannot satisfy `wdt:P235`. |
| Native rank, score and adduct | A [`sio:SIO_000008`](http://semanticscience.org/resource/SIO_000008) attribute on the observation carries a `schema:PropertyValue` with the native field name in `schema:propertyID` and its value in `schema:value`. For example, `CSI:FingerIDScore`, `final_score` and `combined_score` identify three different measures. |
| Wikidata association | Follow `prov:wasDerivedFrom` from the candidate to its reference record, then `rdfs:seeAlso` to the item. Keep the reference key and source separate from the candidate's own descriptors. Compute full-key agreement by comparing complete keys. First-block agreement alone supports a connectivity-level comparison. A reference lacking comparable keys still documents a native association. No `owl:sameAs` assertion is warranted. |

The [ENPKG adapter](../legacy_enpkg/chemicals.py) reads final SIRIUS and reweighted ISDB reports and uses the native structure database where available. The [Flock adapter](../flock/chemicals.py) reads saved annotation hits, chemical-index entries and associated LOTUS structures. Both preserve tied or unresolved candidates. The native score and adduct text belong to their reporting method. No cross-method normalization is implied. The same feature number may refer to different signals across acquisitions or workflows.

## Query both exports

The [sample-to-candidate query](candidates-by-sample.rq) counts assertions by sample, software and procedure. Run it on the first published ENPKG trial from the repository root. Substitute `rdf/flock-first.ttl.gz` to inspect Flock.

```bash
.venv/bin/python - rdf/enpkg-first.ttl.gz <<'PY'
import gzip
import sys
from pathlib import Path
from rdflib import Graph

with gzip.open(sys.argv[1], 'rb') as stream:
    graph = Graph().parse(source=stream, format='turtle')
query = Path('schema/candidates-by-sample.rq').read_text()
for sample, software, procedure, count in graph.query(query):
    print(sample, software, procedure, count, sep='\t')
PY
```

To exercise both native formats without the full workspaces, install [the pinned dependencies](../requirements.txt) and run the following from the repository root:

```bash
.venv/bin/python -B -m unittest test_shared_schema test_chemical_schema test_chemicals_enpkg test_chemicals_flock
```

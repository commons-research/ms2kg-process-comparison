# Shared RDF application profile, version 2

The tracked [`shapes-v2.ttl`](shapes-v2.ttl) is the authoritative common contract for both workflows. Its [W3C SHACL](https://www.w3.org/TR/shacl/) constraints describe the materials, LC–MS acquisitions, raw files, features, annotation procedures, candidates and references in each `reconciled.ttl`. The shapes have local names. Trial data use existing ontology terms.

## Maintain the contract

Edit [`shapes-v2.ttl`](shapes-v2.ttl) when intentionally changing what a conforming graph may or must express. Exercise the intended constraint on a conforming example and a violating example in [`test_shacl.py`](../test_shacl.py). Apply the same contract to both workflows.

The tracked [`fixtures/toy-v2.ttl`](../fixtures/toy-v2.ttl) records the expected material and acquisition facts for the toy dataset. Edit it when those expected facts change and check both adapters against it. Chemical candidates can differ between workflows and do not belong in that fixture.

## Validate a graph offline

Install the [Python dependencies](../requirements.txt) and run the validator from the repository root. Pass each complete reconciled graph as a separate file. Plain and gzip-compressed Turtle are supported.

```sh
workspace=/path/to/completed/workspace
python schema/validate.py "$workspace/enpkg/reconciled.ttl" "$workspace/flock/reconciled.ttl"
```

The validator reads local files without credentials or online lookups. A constraint violation produces a SHACL report naming the offending node and a nonzero exit status. A conforming trial may have no chemical hits or no resolved Wikidata taxon, so it can yield zero [taxon–chemical pairs](../rdf/README.md).

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

## Query one export

The [sample-to-candidate query](candidates-by-sample.rq) counts assertions by sample, software and procedure. Run it on either workflow's `reconciled.ttl`. For a distinct pair comparison between workflows, follow the [offline pair query instructions](../rdf/README.md).

```sh
python - "$workspace/enpkg/reconciled.ttl" <<'PY'
import sys
from pathlib import Path
from rdflib import Graph

graph = Graph().parse(Path(sys.argv[1]), format='turtle')
query = Path('schema/candidates-by-sample.rq').read_text()
for sample, software, procedure, count in graph.query(query):
    print(sample, software, procedure, count, sep='\t')
PY
```

To check the common contract and its adapters against local examples, run the following from the repository root.

```bash
python -B -m unittest test_shacl test_shared_schema test_chemical_schema test_chemicals_enpkg test_chemicals_flock
```

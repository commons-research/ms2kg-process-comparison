# Comparing MS-to-KG ETL pipelines

## Goal

Mass-spectrometry knowledge graphs built by different labs can use incompatible schemas and identifiers, making their data difficult to link. This repository is for documenting and comparing three ways to turn the same [ENPKG toy dataset](https://doi.org/10.5281/zenodo.10018590) into RDF, not for comparing different input datasets. The existing [ENPKG workflow](https://github.com/enpkg/enpkg_full) and [METRIN-KG](https://doi.org/10.1101/2025.08.20.671289) provide context.

## Three pipelines

| Pipeline | Approach | What to provide |
| --- | --- | --- |
| ENPKG reference | Run the [published ENPKG workflow](https://github.com/enpkg/enpkg_full) on its documented toy dataset. | Start with the [legacy benchmark instructions](legacy_enpkg/README.md); pin the upstream revision/configuration and record inputs and output RDF files. |
| Declarative mapping | Map the same source data to RDF using [RML](https://rml.io/) and an RML engine. | Commit mapping rules, engine version, and any documented source-preparation steps. |
| Programmatic mapping | Map the same source data to RDF with code, for example [Python/RDFLib](https://rdflib.readthedocs.io/en/stable/gettingstarted/). | Commit source code, locked dependencies, and an entry point. |

The ENPKG evaluation runner is in `legacy_enpkg/`; it checks out the external workflow rather than vendoring it. RML and programmatic tracks are not yet implemented here.

The [Isla Gabriola flock benchmark guide](flock/README.md) documents a separate source-to-graph pipeline on the same toy release. Its Mato `run` command includes input preparation and graph export; use the guide's export-only timing when comparing it with the legacy ENPKG graph stage.

## Minimum requirements for each track

1. Use the same [toy-dataset release 0.2](https://doi.org/10.5281/zenodo.10018590); record the archive checksum and exact input files consumed. Keep raw inputs unchanged and out of version control. If one workflow requires enrichment or preprocessing, document it and use the same prepared inputs across tracks for any like-for-like ETL comparison; otherwise report the extra stage separately.
2. Publish a source-to-RDF mapping for the *shared* scope before comparing results: the available sample, mass-spectral feature, and annotation identifiers and their relationships. State which fields are absent from the dataset or outside scope. Use the same classes, predicates, URI construction rules, datatypes, and controlled vocabularies for that scope in all three tracks; document any ENPKG-specific triples outside it.
3. Provide a clean-start command, required tool versions/configuration, input and output paths, and a single command to generate an RDF file (Turtle or N-Triples). Output must parse as RDF, use stable non-blank identifiers for shared entities, retain source provenance, and not embed local machine paths in identifiers.
4. A second run on unchanged inputs must produce the same RDF graph (triple order and serialization need not match). Document errors and any network access, credentials, licenses, or external services required; do not commit secrets.

## Comparison procedure

1. Download and unpack the [toy dataset](https://zenodo.org/records/10018590); record its version and archive checksum. Follow each track's documented clean-start command, using the same machine and equivalent input stage.
2. Parse each RDF output. Check that the agreed entity types and available sample–feature–annotation links exist and that each identifier maps back to the same source record. Compare graphs as RDF triples (account for blank-node equivalence), not as text files; compare the shared scope separately from any extra triples.
3. Run each track at least twice. Record elapsed time, peak memory, output triple count, RDF validity, shared-scope coverage, and whether the two runs produce equivalent graphs. Exclude download/install time from ETL timings, and disclose any preprocessing or external calls.
4. Publish a results table with one row per track: revision/tool versions, input stage, links to mapping/run instructions/output, shared-scope coverage, triple count, elapsed time/peak memory, repeatability, and deviations. Explain mismatches and missing fields rather than ranking pipelines by triple count alone.

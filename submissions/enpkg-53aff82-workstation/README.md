# ENPKG chemical enrichment on the toy dataset

The [measured record](benchmark.json) covers two raw-to-RDF trials of [ENPKG `53aff82d01`](https://github.com/enpkg/enpkg_full/tree/53aff82d01be6856cfd12a9910ddb9fff93dc0bd). The [ENPKG baseline](../enpkg-workstation/README.md) and [Isla Gabriola Flock](../flock-workstation/README.md) used the same six raw acquisitions and sample metadata on the same workstation. The [comparison and plots](../../results/comparison.md) show all six trials separately.

| Measurement | Trial 1 | Trial 2 |
|---|---:|---:|
| Wall time (s) | 621.32 | 605.36 |
| Peak resident memory (KiB) | 131,555,768 | 149,999,812 |
| Distinct triples across the three native Turtle exports | 102,553 | 102,547 |
| Chemical candidate assertions with a Wikidata association | 476 of 697 | 477 of 697 |
| Distinct chemical Wikidata items linked | 936 | 934 |

The positive-mode biological sample `VGF151_E05` contributes the chemical annotations. The blank and QC contribute metadata. The chemical enrichment looks up the 14-character connectivity block of the InChIKey, which can identify several stereoisomers. Multiple Wikidata items can therefore be associated with one candidate. The item count excludes the source taxon. The two native RDF datasets are non-equivalent.

Download the [shared RDF for each trial](../../rdf/README.md) to trace an annotation from its taxon to its candidate and reference. The [pair comparison](../../rdf/pair-summary.md) counts distinct taxon–chemical associations shared with Flock and those proposed by only one workflow.

## Measurement and reproduction

The runner used the [baseline timing protocol, reference files and MZmine batch](../enpkg-workstation/README.md#inputs-and-scientific-scope). Each trial started with fresh MZmine outputs and ran through the final ENPKG export. GNU `time -v` included live SIRIUS and enrichment calls. Preparation, downloading references, and computing graph statistics were outside the timer. Service responses and operating-system caches were not frozen.

The measurement used [comparison runner `3108eef`](https://github.com/commons-research/ms2kg-process-comparison/tree/3108eeff41639e10ca82f2d7cf2cf81d9cef7157) with `legacy_enpkg/prepare.py` pinned to `53aff82d01be6856cfd12a9910ddb9fff93dc0bd`. To run this revision, follow the [ENPKG installation guide](../../legacy_enpkg/README.md) in a separate checkout, use that full hash for both the installed ENPKG checkout and the runner's `REVISION`, then run `make pipeline enpkg`. The default profile pin selects the original baseline. Both measured trials used the same local taxonomy patch as the baseline (patch SHA-256 `748d5c70980623b6e95eb5418037e54c5c449f220822bb6bb9db60b954b86894`). The patch and live service responses are not included in this submission, so the public revisions alone cannot reproduce the exact measured installation and outputs.

Run `make results` at the comparison repository root to regenerate the public plots from submitted records without ETL or credentials. The [record](benchmark.json) contains the canonical input hashes, both timing-report hashes and the filenames, byte counts and SHA-256 hashes for all six native Turtle exports. Candidate-level coverage above was computed from the retained annotations and their associated structure references. Those annotations and the raw graphs are not bundled in the repository.

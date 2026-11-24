# ENPKG workstation baseline

The [measured record](benchmark.json) contains two raw-to-RDF trials for `enpkg` in the same `workstation-raw-to-rdf` cohort as the [Flock baseline](../flock-workstation/README.md). The cohort uses a public machine alias.

| Trial | Wall time (s) | Peak RSS (KiB) | Distinct triples |
|---|---:|---:|---:|
| First | 408.05 | 118,941,700 | 93,576 |
| Second | 415.64 | 135,283,412 | 93,594 |

Each export contains three merged Turtle files in the default graph, with 26 classes, 70 predicates and no blank nodes. The QC and blank files have matching hashes across trials. The biological sample differs. For example, both `SiriusCanopusAnnotation` and `SiriusStructureAnnotation` have 455 instances in the first graph and 456 in the second. The two RDF datasets are unequal. The record does not establish the cause of the difference or the accuracy of any identification.

## Inputs and scientific scope

The [ENPKG toy release 0.2](https://doi.org/10.5281/zenodo.10018590) ZIP has SHA-256 `0c8bc4f8d350999a5b2910774e00cd4731ea32ffacbf2c0828258966583ed450`. The record identifies the sample table and six raw `mzXML` files by SHA-256. `VGF151_E05` is the biological sample, `VGF138_A01` the QC and `VGF140_H12` the blank. All three have positive and negative acquisitions. MZmine processed each acquisition separately with four threads and the [unaligned batch](../../legacy_enpkg/toy-unaligned.mzbatch). ENPKG consumed the resulting GNPS spectra, peak-area tables and SIRIUS inputs. Its configuration selected positive polarity. SIRIUS annotated only the biological sample. The QC and blank contribute metadata graphs. The biological graph also includes features, molecular networking, ISDB, SIRIUS, CANOPUS, Spec2Vec and chemical metadata. Flock exports a different model of the same inputs, so triple counts do not measure relative identification quality.

| Retained input or reference | SHA-256 |
|---|---|
| LC acquisition method from the toy ZIP | `a13c236180292e7f9b04262c54121e0873834f8beee0af0e5b934aa479d2d228` |
| MZmine batch | `7d2132ebf7c517733825aeb682ded2b704704ba9ae6842cc3f99b9b6d3672892` |
| [Frozen LOTUS metadata, compressed](https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1) | `a206b62537733a3e8345598aacec7e8059ab777219d4b867003d49e692a65945` |
| [Positive ISDB library](https://zenodo.org/records/8287341/files/isdb_pos_cleaned.pkl?download=1) | `cb57b8aa96892e7a70278616295802fc35fee653ec5f32e2d329d59d3258cf0b` |

## Fresh run and limits

Follow the [ENPKG installation and reference setup](../../legacy_enpkg/README.md) and [MZmine installation instructions](../../legacy_enpkg/MZMINE.md). The two trial checkouts and provenance files identify [ENPKG `a6535a5dfda9f4c59c79f39401359cb14c521a86`](https://github.com/enpkg/enpkg_full/tree/a6535a5dfda9f4c59c79f39401359cb14c521a86) with its `uv.lock`, plus a local change to `02_enpkg_taxo_enhancer/src/taxo_info_fetcher.py`. The modified file has SHA-256 `deb7eca47dbeeba193578bae0c59b797f5042e84679de57e33994b8c8c41a8a5`. Each trial retains `installed-taxonomy.patch` with SHA-256 `748d5c70980623b6e95eb5418037e54c5c449f220822bb6bb9db60b954b86894`. This submission does not distribute that patch. The public pin alone cannot reconstruct the measured installation.

Both trials logged [MZmine 4.11.0](https://github.com/mzmine/mzmine/releases/tag/v4.11) and SIRIUS 6.5.4. MZmine requires an activated license file or `MZMINE_CLI_TOKEN`. SIRIUS needs authorized service access through `SIRIUS_USERNAME` and `SIRIUS_PASSWORD`. Live taxonomy, annotation and enrichment services have no frozen response set in this submission. The runner used the installed ENPKG Python environment. The currently retained environment declares Python 3.11.12, while the trial provenance records its location only. SIRIUS reported 32 cores and 64 threads in both trials. The benchmark did not capture a machine manifest with CPU model, RAM, OS/kernel, process limits, background load or GNU `time` version.

From the comparison repository root on a provisioned machine, run `MS2KG_COHORT=my-lab make pipeline enpkg`. Use a cohort alias for that machine and resource policy. The [profile](../../pipelines/enpkg.toml) prepares each trial with `bash legacy_enpkg/prepare.sh` outside the timer, then times `bash legacy_enpkg/run.sh` from the repository root using GNU `time -v`. The first and second trials have separate working directories and fresh processed outputs. References and installed tools are shared. No cold operating-system cache condition was recorded. The timer spans raw processing through graph export, including the live services. The recorder subsequently parses the three merged files per trial and compares their union. No separate ontology-conformance result is claimed.

## Evidence and replay

The [record](benchmark.json) is sufficient for `make results` to render this baseline without ETL. Only the summary and hashes are public here. The retained local workspace is `build/enpkg.xy9t5mad`. Both `first/` and `second/` contain `time.txt`, `enpkg-provenance.json` and `enpkg/data/output/standalone_graphs/*.ttl`. The exact six artifact names, in trial order, are in `trials[].rdf`. The archive, seven extracted inputs, both timing reports and all six RDF byte lengths and hashes were checked against the retained files. Both timing reports record exit status zero. No public evidence bundle or access grant is supplied. The installation, potentially sensitive logs, raw graphs and per-trial provenance remain unpublished.

With access to the retained workspace, replay the record without running either pipeline. From the repository root with the comparison dependencies installed, run the following in Bash. It writes only to a new scratch submission and compares the complete decoded records.

```bash
set -eu
work=build/enpkg.xy9t5mad
scratch=$(mktemp -d build/replay.XXXXXXXX)
submission=$scratch/enpkg-workstation
mkdir "$submission"
cp submissions/enpkg-workstation/README.md "$submission/"
.venv/bin/python benchmark.py record --submission "$submission" \
  --pipeline enpkg --cohort workstation-raw-to-rdf --input "$work/input" \
  --first-time "$work/first/time.txt" --first-rdf "$work/first/enpkg/data/output/standalone_graphs/"*.ttl \
  --second-time "$work/second/time.txt" --second-rdf "$work/second/enpkg/data/output/standalone_graphs/"*.ttl
.venv/bin/python -c 'import json,sys; a,b=map(lambda path: json.load(open(path)),sys.argv[1:]); sys.exit(a != b)' \
  "$submission/benchmark.json" submissions/enpkg-workstation/benchmark.json
```

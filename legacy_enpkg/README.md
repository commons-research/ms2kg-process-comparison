# ENPKG workflow including MZmine

```bash
make pipeline enpkg
```

Run this from the comparison repository root after the installation below. The [ENPKG profile](../pipelines/enpkg.toml) starts the clock before MZmine reads the raw spectra and stops after ENPKG exports the standalone Turtle graphs. The runner repeats the workflow in a fresh directory, checks the two RDF datasets for equivalence, and records a successful pair for `make benchmarks`.

## Scope

- **Input.** Six canonical raw spectra and the sample metadata table from [ENPKG toy release 0.2](https://doi.org/10.5281/zenodo.10018590). The LC acquisition method from the release and the checked-in [MZmine batch](toy-unaligned.mzbatch) describe acquisition and processing. No feature tables, spectral exports or annotations from an earlier analysis enter the trial.
- **Preprocessing.** MZmine runs separately for each spectrum. ENPKG receives the GNPS spectra, quantification CSV and SIRIUS spectra. The upstream `params/user.yml` selects positive polarity. The input has one biological sample, one QC and one blank. Upstream SIRIUS selects the biological sample only. This distinction matters when interpreting coverage and comparing triple counts with Flock.
- **Downstream.** The timed job runs the external ENPKG stages for sample organization, MassIVE identifiers, taxonomy, adduct generation, molecular networking and ISDB, SIRIUS and CANOPUS, chemical enrichment, MEMO and graph building. Acquisition of the toy ZIP and reference libraries takes place outside the timer. Live annotation and enrichment calls remain inside it.
- **Results.** Each trial writes graphs to `enpkg/data/output/standalone_graphs/` inside its workspace. `make benchmarks` uses completed records from both pipelines. MZmine intermediate files and isolated stage `10` timings do not qualify.

## One-time setup

Install [MZmine 4.11.0 and configure its license](MZMINE.md). Install [the pinned ENPKG workflow](https://github.com/enpkg/enpkg_full/tree/a6535a5dfda9f4c59c79f39401359cb14c521a86) with its locked Python environment. Set `ENPKG_ROOT` if the checkout lives somewhere other than `legacy_enpkg/upstream`. The following commands are for a fresh installation from the comparison repository root.

```bash
git clone https://github.com/enpkg/enpkg_full.git legacy_enpkg/upstream &&
  git -C legacy_enpkg/upstream checkout --detach a6535a5dfda9f4c59c79f39401359cb14c521a86 &&
  (cd legacy_enpkg/upstream && uv sync --frozen --python 3.11)
```

Stage the two reference files outside the timer in the external checkout. The linked paths identify the files expected by ENPKG.

```bash
(
  set -eu
  cd "${ENPKG_ROOT:-legacy_enpkg/upstream}/03_enpkg_mn_isdb_isdb_taxo"
  mkdir -p db_metadata db_spectra
  curl -fL 'https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1' -o db_metadata/230106_frozen_metadata.csv.gz
  curl -fL 'https://zenodo.org/records/8287341/files/isdb_pos_cleaned.pkl?download=1' -o db_spectra/isdb_pos_cleaned.pkl
)
```

Install SIRIUS 6.5.4 and configure `SIRIUS_USERNAME` and `SIRIUS_PASSWORD` for an account authorized to use its web services. Follow the [upstream installation and credential instructions](https://github.com/enpkg/enpkg_full/blob/a6535a5dfda9f4c59c79f39401359cb14c521a86/README.md#-install-sirius-locally). Keep credentials and raw logs private. The benchmark repository's `.env` is for MZmine, and the external installation has its own credential configuration.

**Reproduction limit.** The installed workstation checkout has a local change to the Wikidata taxonomy client. A clean checkout of the public pin lacks that change. Disclose its provenance for a workstation result. Publish and pin a compatible upstream revision before claiming that another lab can reproduce the patched workflow from public source alone. SIRIUS and live enrichment results also depend on service access and state at run time.

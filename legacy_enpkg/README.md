# ENPKG workflow including MZmine

```bash
make compare
```

Run this from the comparison repository root after provisioning both workflows. Each invocation times one fresh [ENPKG trial](../pipelines/enpkg.toml) and one fresh [Flock trial](../flock/README.md) on the same verified input. ENPKG timing starts before MZmine reads the raw spectra and ends after the native Turtle export.

## Scope

- **Input.** Six canonical raw spectra and the sample metadata table from [ENPKG toy release 0.2](https://doi.org/10.5281/zenodo.10018590). The LC acquisition method from the release and the checked-in [MZmine batch](toy-unaligned.mzbatch) describe acquisition and processing. No feature tables, spectral exports or annotations from an earlier analysis enter the trial.
- **Preprocessing.** MZmine runs separately for each spectrum. ENPKG receives the GNPS spectra, quantification CSV and SIRIUS spectra. The upstream `params/user.yml` selects positive polarity. The input has one biological sample, one QC and one blank. Upstream SIRIUS selects the biological sample only. This distinction matters when interpreting coverage and comparing triple counts with Flock.
- **Downstream.** The timed job runs the external ENPKG stages for sample organization, MassIVE identifiers, taxonomy, adduct generation, molecular networking and ISDB, SIRIUS and CANOPUS, chemical enrichment, MEMO and graph building. Acquisition of the toy ZIP and reference libraries takes place outside the timer. Live annotation and enrichment calls remain inside it.
- **Results.** Inside `runs/run-*/enpkg/`, the native graphs are in `enpkg/data/output/standalone_graphs/`. The runner writes `reconciled.ttl` in the trial directory and validates it against the common [shapes](../schema/shapes-v2.ttl) outside the timer. The run's `comparison.tsv` reports raw-to-native wall time, peak resident memory and distinct triple counts for each representation.

## One-time setup

Install [MZmine 4.11.0 and configure its license](MZMINE.md). Install [ENPKG at the fixed revision](https://github.com/enpkg/enpkg_full/tree/53aff82d01be6856cfd12a9910ddb9fff93dc0bd) with its locked Python environment. From the comparison repository root, use the commands below for a fresh installation. Set `ENPKG_ROOT` to an absolute path to install elsewhere.

```bash
(
  set -eu
  installed=${ENPKG_ROOT:-legacy_enpkg/upstream-fixed}
  git clone https://github.com/enpkg/enpkg_full.git "$installed"
  git -C "$installed" checkout --detach 53aff82d01be6856cfd12a9910ddb9fff93dc0bd
  git -C "$installed" apply "$PWD/legacy_enpkg/patches/taxonomy.patch"
  cd "$installed"
  uv sync --frozen --python 3.11
)
```

Stage the two reference files outside the timer in the external checkout. The linked paths identify the files expected by ENPKG.

```bash
(
  set -eu
  cd "${ENPKG_ROOT:-legacy_enpkg/upstream-fixed}/03_enpkg_mn_isdb_isdb_taxo"
  mkdir -p db_metadata db_spectra
  curl -fL 'https://zenodo.org/records/7534071/files/230106_frozen_metadata.csv.gz?download=1' -o db_metadata/230106_frozen_metadata.csv.gz
  curl -fL 'https://zenodo.org/records/8287341/files/isdb_pos_cleaned.pkl?download=1' -o db_spectra/isdb_pos_cleaned.pkl
)
```

Install SIRIUS 6.5.4 at `sirius-install/sirius/bin/sirius` inside the external checkout or set `PATH_TO_SIRIUS` to its absolute executable path. Configure `SIRIUS_USERNAME` and `SIRIUS_PASSWORD` for an authorized account following the [upstream instructions](https://github.com/enpkg/enpkg_full/blob/53aff82d01be6856cfd12a9910ddb9fff93dc0bd/README.md#-install-sirius-locally). Keep the external checkout's `.env` and the trial's `sirius.log` private. The comparison repository's `.env` is for MZmine.

The [taxonomy patch](patches/taxonomy.patch) pins the workstation's Wikidata query, request headers, timeout and HTTP error handling. Its SHA-256 is `748d5c70980623b6e95eb5418037e54c5c449f220822bb6bb9db60b954b86894`. Preparation checks the revision and patched source digest, rejects other tracked changes, and records the diff in `installed-taxonomy.patch` alongside `enpkg-provenance.json` in the fresh ENPKG trial directory. SIRIUS and live enrichment responses depend on service access and state at run time.

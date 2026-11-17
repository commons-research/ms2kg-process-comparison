# Isla Gabriola flock: toy-dataset benchmark (macOS)

[Isla Gabriola flock](https://github.com/oolonek/isla-gabriola-flock) is an overview, not the executable. [Mato](https://github.com/oolonek/mato/blob/master/TECHNICAL.md#example-download-the-zenodo-toy-dataset-and-export-a-kg) coordinates the same [ENPKG toy release 10018590](https://zenodo.org/records/10018590) used by the [legacy ENPKG runner](../legacy_enpkg/README.md). Mato's current entry point is **`run`**, not `bootstrap`.

## Install

Install Apple Command Line Tools (`xcode-select --install` if needed), Git and [Rust/Cargo](https://rustup.rs/) with edition-2024 support (Rust 1.85+). Use a writable source directory outside this repository. The seven species, Mato and Hocofaisan's library dependency must be siblings:

```sh
FLOCK="$HOME/isla-gabriola-flock"
mkdir -p "$FLOCK"
for repo in sapayoa machaca peregrino cunaguaro picoto hocofaisan mato; do
    git clone "https://github.com/oolonek/$repo.git" "$FLOCK/$repo"
done
git clone "https://github.com/earth-metabolome-initiative/spectral-matcher.git" "$FLOCK/spectral-matcher"
cargo build --release --locked --manifest-path "$FLOCK/mato/Cargo.toml"
```

If repositories already exist, **do not clone over them**. Inspect `git -C "$FLOCK/mato" status --short` and the other checkouts for local changes before pulling. For clean checkouts, fast-forward every repository (including `spectral-matcher`), rebuild, and record exact commits:

```sh
for repo in sapayoa machaca peregrino cunaguaro picoto hocofaisan mato spectral-matcher; do
    git -C "$FLOCK/$repo" pull --ff-only || break
    printf '%s ' "$repo"
    git -C "$FLOCK/$repo" rev-parse HEAD
done
cargo build --release --locked --manifest-path "$FLOCK/mato/Cargo.toml"
```

Keep the printed revisions and Cargo/Rust versions. Mato builds the selected species on demand; `spectral-matcher` is a library, not a pipeline stage.

## Configure and run

```sh
WORKSPACE="$HOME/isla-gabriola-toy-run1"
mkdir -p "$WORKSPACE"
test -e "$FLOCK/mato/config/toy.local.toml" || cp "$FLOCK/mato/config/toy.toml" "$FLOCK/mato/config/toy.local.toml"
```

Set the **absolute** `workspace = "..."` in `toy.local.toml` to the existing `$WORKSPACE`; keep `flock_root = "../.."`. If that ignored local config predates Mato's `run` entry point, compare it with `config/toy.toml`: it needs `[dataset.archive] doi = "10.5281/zenodo.10018590"`, the `[annotation.library_source]` and `[annotation.lotus_source]` sections, `[indexes] create_missing = true`, and the ordered `kg_export`, `kg_validate` stages after `chemical_enrich`. Do not overwrite a configured job blindly. The template's `[dataset].doi = "10.5281/zenodo.10018264"` is the *concept DOI*, not the archive release DOI.

```sh
"$FLOCK/mato/target/release/mato" run --config "$FLOCK/mato/config/toy.local.toml"
"$FLOCK/mato/target/release/mato" inspect --config "$FLOCK/mato/config/toy.local.toml"
```

On a fresh workspace, run **before** `inspect`: current `inspect` requires the dataset root to exist, while `run` downloads and extracts it.

`run` downloads/verifies the configured archive and annotation references, builds missing shared Wikidata snapshots from QLever, runs validation, ingestion, taxon enrichment, Picoto, registration, positive-MS2 annotation and chemical enrichment, then exports a **new** N-Quads graph and runs SHACL validation. It prints a graph path and writes a Markdown report beside the job SQLite database. Allow disk and network capacity for the ~939 MB reference MGF, LOTUS metadata and multi-million-row snapshots. No Python, SIRIUS, GraphDB, `curl` or `unzip` is required. A partial annotation run can exit nonzero; inspect its report rather than treating a valid graph as proof all files were annotated. The toy config refuses partial export by default.

```sh
shasum -a 256 "$WORKSPACE"/sapayoa/zenodo-10018590/*.zip
"$FLOCK/mato/target/release/mato" show annotation_current_runs --config "$FLOCK/mato/config/toy.local.toml" --limit 20
```

Keep archive digest, input paths, config, all source revisions, graph path, report, hardware and any network or preparation failures with the benchmark results. Never commit source datasets, references or generated graphs to this repository.

## Measure graph export against the legacy runner

The legacy runner times **RDF generation only**, after preparation. A first `mato run` includes downloads, indexing, building species, processing and validation; timing it as if it were export-only is not comparable. After a successful full run, inspect the dataset table and read the row ID for the toy DOI (it need not be `1`):

```sh
"$FLOCK/mato/target/release/mato" show datasets --config "$FLOCK/mato/config/toy.local.toml"
DATASET_ID=REPLACE_WITH_PRINTED_ID
DB="$WORKSPACE/mato/toy.sqlite"
GRAPH="$WORKSPACE/mato/toy-kg/benchmark-1.nq"
/usr/bin/time -l "$FLOCK/peregrino/target/release/peregrino" kg export --db "$DB" --dataset-id "$DATASET_ID" --out "$GRAPH" > "$WORKSPACE/export.log" 2> "$WORKSPACE/export-time-and-errors.txt"
"$FLOCK/peregrino/target/release/peregrino" kg validate --graph "$GRAPH"
wc -l "$GRAPH"
```

The `time -l` stderr includes both export progress/errors and elapsed time/maximum resident size. Validation is **outside** the timed command. `wc -l` counts N-Quads statements, not necessarily distinct RDF triples across named graphs; parse and compare RDF semantics for the agreed shared scope. Export refuses to overwrite an existing graph: use a new filename for another attempt. For an independent full-run replicate use a **new empty workspace** and point a separate local job config at it; reusing the existing job preserves species state and is not a fresh run. Do not reset an existing job without inspecting the selected paths and intentionally discarding its data.

Flock's evidence graph and ENPKG's graph have different semantics and may include different enrichment. Disclose those differences and compare the shared mapping scope separately rather than ranking by total statement count. See the [comparison criteria](../README.md#minimum-requirements-for-each-track) and [Peregrino's graph semantics](https://github.com/oolonek/peregrino/blob/master/TECHNICAL.md#wikidata-linked-local-knowledge-graph).

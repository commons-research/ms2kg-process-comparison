# Legacy ENPKG evaluation (macOS)

This directory runs the [ENPKG full workflow](https://github.com/enpkg/enpkg_full) at commit `a6535a5dfda9f4c59c79f39401359cb14c521a86` against [toy dataset 0.2](https://doi.org/10.5281/zenodo.10018590). `run.sh` prepares the data with the original workflow stages 01–09, then times stage 10 (RDF generation) with macOS `/usr/bin/time -l`. Downloads, enrichment, SIRIUS analysis, and installation are **not** included in the measured time. The upstream checkout is ignored; any local source correction must be recorded as a patch, not mistaken for the unmodified baseline.

## Install and configure

From the root of this repository on macOS, install `wget` and `jq` with the available package manager (this workstation has MacPorts; use `brew install wget jq` instead if you use Homebrew). [`uv`](https://docs.astral.sh/uv/getting-started/installation/) is already installed here; install it first if it is missing on your machine.

```sh
sudo port install wget jq
uv python install 3.11
git clone https://github.com/enpkg/enpkg_full.git legacy_enpkg/upstream
git -C legacy_enpkg/upstream checkout --detach a6535a5dfda9f4c59c79f39401359cb14c521a86
(cd legacy_enpkg/upstream && uv sync --frozen --python 3.11)
cp legacy_enpkg/upstream/.env.example legacy_enpkg/upstream/.env
chmod 600 legacy_enpkg/upstream/.env
${EDITOR:-vi} legacy_enpkg/upstream/.env
```

### SIRIUS

The pinned ENPKG checkout includes `src/install_sirius.sh`, which downloads and unpacks the newest stable release for your OS/architecture. It requires `wget`, `jq`, `unzip`, and `curl`. Run it **from the upstream root** after cloning:

```sh
(cd legacy_enpkg/upstream && bash src/install_sirius.sh "$PWD/sirius-install" macos x64)
```

The installer prints its installation directory and executable hint. Set `PATH_TO_SIRIUS` in `legacy_enpkg/upstream/.env` to the executable's **absolute path**, then set `SIRIUS_USERNAME` and `SIRIUS_PASSWORD` for CSI:FingerID/CANOPUS web services. The pinned `params/user.yml` requests SIRIUS major version 6; check the installed binary's version before evaluation. At the time of writing, the latest release is [6.5.4](https://github.com/sirius-ms/sirius/releases/tag/v6.5.4), but the installer does **not** pin it: if a later major release is selected, use a [versioned 6.x release](https://github.com/sirius-ms/sirius/releases) instead. See the [SIRIUS 6 installation guide](https://v6.docs.sirius-ms.io/install/).

Check `params/user.yml` before starting: its default record is `10018590`, polarity is `pos`, and `graph-builder.graph_output_dir_path` is `../data/output/standalone_graphs` (relative to the graph-builder module). Keep these defaults for the baseline, and record any changes. No GraphDB installation is required to export Turtle.

Optionally download the archive yourself to preserve its checksum before upstream extraction deletes the ZIP (otherwise the workflow downloads it automatically, and you must obtain the checksum separately):

```sh
mkdir -p legacy_enpkg/upstream/data/input legacy_enpkg/results
curl -fL 'https://zenodo.org/records/10018590/files/enpkg_toy_dataset.zip?download=1' -o legacy_enpkg/upstream/data/input/enpkg_toy_dataset.zip
shasum -a 256 legacy_enpkg/upstream/data/input/enpkg_toy_dataset.zip | tee legacy_enpkg/results/input-sha256.txt
```

If direct download fails, download the same record through a browser into that path and run the `shasum` command. Never commit the downloaded dataset, credentials, or external databases.

## Run and inspect

```sh
sh legacy_enpkg/run.sh
```

The script refuses pre-existing `upstream/data/output` or `upstream/sql_db` in fresh mode; use a fresh checkout for each independent run rather than silently reusing derived data. Each attempt writes `legacy_enpkg/results/run-*/prepare.log`, `graph.log`, `time.txt`, `run-mode.txt`, and `upstream-changes.patch` (the exact local diff). Successful runs additionally write `graphs.json` with per-file triple counts and SHA-256 digests; the RDF is in `legacy_enpkg/upstream/data/output/standalone_graphs/`. To inspect a run, use the specific `run-*` directory printed by the script:

```sh
cat legacy_enpkg/results/run-XXXXXXXX/time.txt
cat legacy_enpkg/results/run-XXXXXXXX/graphs.json
```

Replace `run-XXXXXXXX` with the printed directory name. `time.txt` reports real/user/system time and maximum resident set size; on macOS the latter is in bytes. The runner validates that exported merged Turtle files parse; it cannot guarantee upstream stage scripts failed fast internally, so inspect `prepare.log` and `graph.log` for warnings or hidden failures. An output-file SHA-256 change alone does **not** prove the RDF graph changed (Turtle statement order may vary). For a second independent run, keep the first results, move the old checkout outside `legacy_enpkg/upstream`, and repeat the installation/clone commands in a clean checkout. Record the dataset digest, tool/SIRIUS versions, hardware, preparation steps, graph counts, and deviations beside the timing when reporting results. Network-dependent enrichment may differ between runs.

### Recover from the Wikidata taxonomy lookup error

The upstream taxonomy fetcher queries `https://query.wikidata.org/sparql` without a descriptive User-Agent and tries to parse the response as JSON regardless of HTTP status. The observed failure occurred at this external lookup, *after* the sample architecture was created. An equivalent lookup with the OTT value directly bound to `wdt:P9157` returned the expected Wikidata ID for the failed sample. [The recorded patch](patches/wikidata-taxonomy.patch) applies that indexed query, a descriptive User-Agent, JSON negotiation, and HTTP status checking; it does **not** skip taxonomy enrichment. It changes preparation results but not the timed graph-builder code.

The patch has already been applied to the current ignored checkout. For a new checkout at the pinned revision, apply it once from this repository's root:

```sh
git -C legacy_enpkg/upstream apply ../patches/wikidata-taxonomy.patch
```

If stages 01–02 completed and stage 03 failed before any later stages ran, resume without deleting the partial data:

```sh
sh legacy_enpkg/run.sh --resume-from-taxonomy
```

This restarts at stage 03, recomputing taxonomy (`taxo-info-fetching.recompute: True` in the default config), then runs the remaining preparation stages before timing stage 10. The runner rejects a resume if later database/graph outputs exist. Label its result a **resumed preparation**, not an independent fresh run; use a new checkout and `sh legacy_enpkg/run.sh` for a clean replicate. Record the patch alongside the baseline result. If Wikidata responds with HTTP 429/5xx or a timeout, the dependency is unavailable or rate-limited; keep the failure and retry later rather than inventing missing Wikidata identifiers.

# MZmine for the ENPKG raw-input benchmark

MZmine is the first timed stage of the [ENPKG workflow](README.md). Install it and configure a license before launching the full workflow from the comparison repository root.

```sh
make pipeline enpkg
```

In each trial MZmine processes the six spectra separately with four threads. Intermediate exports are under `build/enpkg.*/{first,second}/output/`. ENPKG consumes the selected polarity and continues through RDF export under the same timer.

## Install MZmine 4.11.0

Use the [official `v4.11` release](https://github.com/mzmine/mzmine/releases/tag/v4.11), which reports MZmine `4.11.0`. Match the batch version so that loading it does not silently change parameters. The release has macOS, Windows and Linux packages and bundles Java. On 64-bit Debian or Ubuntu, download and verify the published package before installing it.

```bash
work=$(mktemp -d "$HOME/ms2kg-enpkg.XXXXXXXX")
installer="$work/mzmine_4.11.0_amd64.deb"
curl -fL https://github.com/mzmine/mzmine/releases/download/v4.11/mzmine_4.11.0_amd64.deb -o "$installer" &&
  printf '%s  %s\n' 0f16ee5bdd24c134a0feb8aa344ae1278d518b97583f66bd1f5cbe87f50f4c7f "$installer" | sha256sum -c - &&
  sudo mkdir -p /usr/share/desktop-directories &&
  sudo apt install "$installer"
```

Without administrator rights, extract the whole Linux portable ZIP from the same release into a user-writable directory. Set `MZMINE_BIN` to its `bin/mzmine` path if `mzmine` is unavailable on `PATH`. The launcher also requires Bash, GNU Make, Python 3.11 or later and `curl` if downloading the dataset. See the [official Linux guide](https://mzmine.github.io/mzmine_documentation/latest/install_linux.html) for missing desktop libraries.

## Set up a CLI token on the benchmark host

A token lets a headless batch claim an available online license without running `--login` on the server. If the browser login launched by MZmine reports `Invalid parameter: redirect_uri`, open the account console directly in a browser on your own computer.

1. Sign in to the [mzio account console](https://auth.mzio.io/realms/mzio/account/). New users choose **Register**, verify their email and check **Licenses** for an eligible license.
2. Open [**CLI tokens**](https://auth.mzio.io/realms/mzio/account/mzio-CliTokens), enter a descriptive name such as `enpkg-benchmark`, and create the token. Copy it immediately. The console shows it once.
3. On the benchmark host, open a terminal in the comparison repository root. Run the following commands in Bash. They create an owner-only `.env` from the empty template on a new checkout and preserve an existing file.

```bash
(
  set -eu
  umask 077
  if [[ ! -e .env ]]; then
    (set -C; cat .env.example > .env)
  fi
  chmod 600 .env
  nano -I .env
)
```

4. In the editor, paste the token between the single quotes on the `MZMINE_CLI_TOKEN=''` line. Add that line if missing. Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`. Keep the populated `.env` on the benchmark host. Share only `.env.example`. Never paste the token into a shell command, chat or pull request.

**Shared-server warning.** MZmine `4.11.0` accepts the token as a process argument and writes command arguments to debug logs. Anyone able to inspect the process arguments or read those logs can use the license. Use this method only where process arguments are private to trusted users. The launcher restricts new files and existing MZmine logs in the home directory. Keep raw logs and timing reports containing expanded commands out of submissions. For a [machine-specific offline license](https://mzmine.github.io/mzmine_documentation/latest/services/users.html#offline-use), set `MZMINE_LICENSE_FILE` to its absolute path instead of creating a token.

Each simultaneous token-authenticated run needs an available license and network access. A token expires after 30 days of inactivity. If exposed, revoke it immediately under **Account security → Device activity** by signing out `mzio pipeline / <token name>`, then generate a replacement. See the [official CLI token guide](https://mzmine.github.io/mzmine_documentation/latest/services/users.html#cli-tokens).

## Input and batch provenance

The launcher uses `build/enpkg_toy_dataset.zip` if present, otherwise it downloads [toy release 0.2](https://zenodo.org/records/10018590). Set `ENPKG_ARCHIVE` to use a ZIP stored elsewhere. If Zenodo refuses the terminal download, save the ZIP from the record page as `build/enpkg_toy_dataset.zip` and rerun the same command. Every source goes through the same [archive and file checksums](../benchmark_input.py).

The versioned [toy batch](toy-unaligned.mzbatch) derives from the [MAPP reference batch at `c4669e7`](https://github.com/commons-teaching/sa2026-dbgi/blob/c4669e799e201c69153082e35a6b7efe2c77c9fe/docs/mapp_project_00050/mapp_batch_00283/results/mzmine/mapp_batch_00283.mzbatch). It uses per-spectrum feature lists, omits alignment and study-specific paths, and exports GNPS spectra, a `SIMPLE` peak-area table and SIRIUS spectra. The [MZmine CLI](https://mzmine.github.io/mzmine_documentation/latest/commandline_tool.html) supplies the input file and output stem for each run.

## Verify the ENPKG handoff

The MZmine `4.11.0` exporters append these suffixes to each CLI output stem. Check the three files in each spectrum's output directory.

| File | ENPKG use |
| --- | --- |
| `<stem>_iimn_fbmn.mgf` | GNPS MS2 spectra |
| `<stem>_iimn_fbmn_quant.csv` | Legacy quantification table with `row ID`, `row m/z`, `row retention time` and exactly one `Peak area` column |
| `<stem>_sirius.mgf` | SIRIUS spectra |

Stage only these files, with names unchanged, in the external ENPKG checkout's configured `source_path`. The [ENPKG organizer](https://github.com/enpkg/enpkg_full/blob/a6535a5dfda9f4c59c79f39401359cb14c521a86/01_enpkg_data_organization/src/create_architecture.py#L59-L147) matches their names against the raw filename stems in the sample TSV and renames them by sample and polarity. An extra matching CSV can overwrite the quantification table. Keep the sample TSV byte-identical to the canonical input.

The [ENPKG launcher](README.md) performs the handoff inside each timed trial.

# Contribute a benchmark

To inspect the measurements, open the [published comparison](results/comparison.md). To run an existing pipeline privately, use its [ENPKG](legacy_enpkg/README.md) or [Flock](flock/README.md) guide. This page is for submitting results or registering another pipeline.

## 1. Fork and choose the profile

Fork [the comparison repository](https://github.com/commons-research/ms2kg-process-comparison/fork). On Linux with Git, GNU Make, GNU `time` at `/usr/bin/time` and Python 3.11 or later, clone your fork and start a branch. The examples use Bash. Replace the profile and cohort with the names for your contribution before running the blocks in the same terminal.

```bash
read -rp 'GitHub fork owner: ' owner
git clone "https://github.com/$owner/ms2kg-process-comparison.git" && cd ms2kg-process-comparison
profile=enpkg
cohort=my-lab-raw-to-rdf
submission="submissions/$profile-$cohort"
git switch -c "benchmark/$profile-$cohort"
```

A cohort identifies a physical machine **and** a timing protocol. Use a public alias. Reuse a cohort only when hardware, resource limits and cache conditions are comparable. Use a unique submission name, at most 40 lowercase letters, digits and separating hyphens. Preserve previously published measurements.

**Existing pipeline?** Follow its setup guide and skip to step 2. **New pipeline?** Add `pipelines/<name>.toml` and a setup guide. Each submission names its runnable profile. Keep the ETL implementation in its external repository. These files describe how to invoke it on the benchmark inputs.

| Profile field | Contract |
| --- | --- |
| `command` | Executable and arguments as an array, run from the comparison repository root. Include every step from the first use of the raw spectra through final RDF export. |
| `rdf` | Array of paths or glob patterns relative to the trial directory for all final `.ttl`, `.nt` or `.nq` files. Use N-Quads for named graphs. |
| `prepare` | Optional executable and arguments for staging the pinned tools, references and configuration before each timer starts. No sample-derived features, annotations or outputs. |

Both commands receive `MS2KG_INPUT` (six verified `mzXML` files under `msdata/raw` and `metadata/metadata.tsv`), `MS2KG_WORK` (fresh trial directory), `MS2KG_ROOT` (comparison repository root) and `MS2KG_CONFIG` (profile path). The optional `[settings]` table is for adapter-specific parameters. The launcher passes arguments directly. A shell adapter must be explicitly named. See the [ENPKG profile](pipelines/enpkg.toml) and [Flock profile](pipelines/flock.toml).

## 2. Measure once, preview and review the evidence

```bash
MS2KG_COHORT="$cohort" make pipeline "$profile" && make benchmarks
```

This single pipeline command measures **two** sequential trials, verifies the canonical input, checks the RDF and retains the original evidence. Installation, reference downloads and plotting are outside the timer. Non-equivalent RDF is a measured outcome. Failed trials do not contribute a result. If the toy ZIP is already on disk, set `ENPKG_ARCHIVE` to its path before running. The automatic download and a local ZIP pass the same SHA-256 checks.

Open `build/comparison.md` for the private preview. Keep the workspace path printed by the launcher. If both trials finished but recording was interrupted, recover them without launching the ETL:

```bash
read -erp 'Completed workspace directory: ' workspace
.venv/bin/python -B pipeline.py --recover "$workspace" --cohort "$cohort" && make benchmarks
```

Review the trial evidence before publishing. Record the full external revisions and reference hashes, effective filtering, machine and timing protocol, service dependencies and any local modifications. Archive reviewed RDF and timing reports externally when permitted. Link the version and checksum in the runbook. If files cannot be shared, state which, why, and what can still be independently verified. Raw logs can expose credentials, especially MZmine command arguments. Never upload the workspace wholesale.

## 3. Submit the record and regenerate the public report

Use the generated `benchmark.json` and write a public runbook from the template. The workspace runbook contains local paths. Keep that one private. If entering from step 2 without recovery, give the path printed by the pipeline command at the prompt.

```bash
read -erp 'Completed workspace directory: ' workspace
mkdir -- "$submission" &&
  cp "$workspace/record/$profile/benchmark.json" "$submission/benchmark.json" &&
  cp submissions/runbook-template.md "$submission/README.md" &&
  "${EDITOR:-vi}" "$submission/README.md" &&
  make results
```

`results/comparison.md` and its linked plots are generated solely from `submissions/`. Each trial has its own measurements. Compare times within a cohort and interpret graph size alongside the runbooks. Review the record for machine-local paths and sensitive identifiers. For a new pipeline, also stage its setup guide and any benchmark-specific adapter or configuration by name.

```bash
git add -- "pipelines/$profile.toml" "$submission" results/
git diff --cached --stat
git commit -m "Benchmark $profile on $cohort" && git push -u origin HEAD
```

On GitHub, choose **Compare & pull request** for the pushed branch, select `commons-research/ms2kg-process-comparison` and base `main`, fill in the pull request template and submit. For early discussion, push the profile or runbook first and use a draft PR. Complete the evidence and generated report before marking it ready. CI checks the submitted records and committed plots without running external pipelines, fetching evidence or using service credentials.

## Independently replay an archived result

Check out the submission revision, follow the runbook to obtain the two timing reports and complete RDF exports, and verify their supplied hashes. Use `benchmark_input.py prepare` to extract the canonical input from the pinned ZIP. `benchmark.py record --help` describes the evidence-only recorder, including `--input`, `--pipeline`, `--cohort` and the two timing/RDF pairs. Write the replay into a separate directory containing a `README.md` and compare its `benchmark.json` with the submitted record. Redactions to published timing files change their hashes and must be documented. Running `make pipeline NAME` measures new trials instead.

# Compare taxon–chemical candidate pairs

`make compare` writes `enpkg/reconciled.ttl` and `flock/reconciled.ttl` under one `runs/run-*` workspace. Each graph describes one workflow's trial on the same raw inputs using the [common application profile](../schema/README.md). Keep the graphs separate so each pair can be attributed to the workflow that reported it.

## Query a completed workspace offline

With the [Python dependencies](../requirements.txt) installed, run these commands from the repository root. Set `workspace` to the completed run directory. Neither command needs service credentials, Wikidata access or native workflow software.

```sh
workspace=/path/to/completed/workspace
python schema/validate.py "$workspace/enpkg/reconciled.ttl" "$workspace/flock/reconciled.ttl"
python rdf/compare_pairs.py --input-dir "$workspace" --output-dir "$workspace"
```

`pair-summary.md` counts distinct Wikidata taxon–chemical pairs found by each workflow, by both, or by only one. It also breaks the counts down by software and procedure. `pair-evidence.tsv` identifies the workflow, software, procedure and key agreement for each association. A pair counts once per workflow even if several methods or features support it.

The [pair query](taxon-chemical-pairs.rq) starts at the biological sample, reads the reported taxon of its source, and follows its acquisition and raw file to an annotated feature. It takes the chemical item from the candidate’s reference record. `full-key` means the candidate and reference have matching complete InChIKeys. `connectivity-only` means they share the first block without a full-key match. `unverified` retains native associations with missing or conflicting keys. A shared pair does not establish feature alignment or confirm compound presence in the source organism.

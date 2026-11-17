#!/bin/sh
# Run ENPKG preparation outside the timed section, then time RDF generation.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
upstream="$here/upstream"
revision=a6535a5dfda9f4c59c79f39401359cb14c521a86

if [ ! -d "$upstream/.git" ]; then
    echo "Clone ENPKG into $upstream first (see README.md)." >&2
    exit 1
fi
if [ "$(git -C "$upstream" rev-parse HEAD)" != "$revision" ]; then
    echo "Expected upstream revision $revision; do not benchmark a different checkout." >&2
    exit 1
fi
if [ ! -x "$upstream/.venv/bin/python" ] || [ ! -f "$upstream/.env" ]; then
    echo "Install upstream dependencies and configure upstream/.env first." >&2
    exit 1
fi
if [ ! -x /usr/bin/time ] || [ "$(uname -s)" != Darwin ]; then
    echo "This runner measures peak memory using macOS /usr/bin/time -l." >&2
    exit 1
fi
mode=${1:-fresh}
if [ "$#" -gt 1 ] || { [ "$mode" != fresh ] && [ "$mode" != --resume-from-taxonomy ]; }; then
    echo "Usage: sh legacy_enpkg/run.sh [--resume-from-taxonomy]" >&2
    exit 2
fi
if [ "$mode" = fresh ] && { [ -e "$upstream/data/output" ] || [ -e "$upstream/sql_db" ]; }; then
    echo "Existing upstream outputs/database detected. Use a fresh checkout for an independent run; no data was deleted." >&2
    exit 1
fi
if [ "$mode" = --resume-from-taxonomy ] && {
    [ ! -d "$upstream/data/output/individual_analysis" ] ||
    [ -e "$upstream/sql_db" ] ||
    [ -e "$upstream/data/output/standalone_graphs" ];
}; then
    echo "Resume requires stage 01–02 outputs, with no downstream database or exported graphs; no data was deleted." >&2
    exit 1
fi

mkdir -p "$here/results"
result=$(mktemp -d "$here/results/run-XXXXXXXX")
printf '%s\n' "$revision" > "$result/upstream-revision.txt"
printf '%s\n' "$mode" > "$result/run-mode.txt"
git -C "$upstream" diff --binary > "$result/upstream-changes.patch"
printf 'Logs and measurements: %s\n' "$result"

# The legacy entry point does not stop on every failed sub-step. Run each stage
# separately so a stage-level failure cannot be hidden by a later stage.
(
    cd "$upstream"
    PATH="$PWD/.venv/bin:$PATH"
    export PATH
    set -a
    . ./.env
    set +a
    stages="03_workflow_taxo_enhancer.sh 04_workflow_dl_ressources.sh 05_workflow_make_adducts.sh 06_workflow_annotate_mn_isdb.sh 07_workflow_annotate_sirius.sh 08_workflow_chemo_info_fetcher.sh 09_workflow_memo.sh"
    if [ "$mode" = fresh ]; then
        stages="01_0_workflow_data_download.sh 01_1_workflow_create_architecture.sh 02_workflow_massive_id.sh $stages"
    fi
    for stage in $stages
    do
        printf '\n=== %s ===\n' "$stage"
        sh "workflow/$stage" || exit 1
    done
) > "$result/prepare.log" 2>&1 || {
    echo "Preparation failed; see $result/prepare.log" >&2
    exit 1
}

(
    cd "$upstream"
    PATH="$PWD/.venv/bin:$PATH"
    export PATH
    set -a
    . ./.env
    set +a
    /usr/bin/time -l sh workflow/10_workflow_graph_builder.sh
) > "$result/graph.log" 2> "$result/time.txt" || {
    echo "RDF generation failed; see $result/graph.log and $result/time.txt" >&2
    exit 1
}

"$upstream/.venv/bin/python" "$here/check_graph.py" \
    "$upstream/data/output/standalone_graphs" > "$result/graphs.json" || {
    echo "RDF validation failed; see $result/graphs.json and $result/graph.log" >&2
    exit 1
}
printf 'RDF validated. Graph manifest: %s/graphs.json; timing: %s/time.txt\n' "$result" "$result"

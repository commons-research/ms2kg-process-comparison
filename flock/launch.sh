#!/usr/bin/env bash
set -euo pipefail

job="${MS2KG_WORK:?}/flock"
checkouts=$(realpath -e -- "${FLOCK_ROOT:-$HOME/git_repos/oolonek/isla-gabriola-flock}")
# Mato resolves a relative target directory against its invocation directory.
if [[ -n ${CARGO_TARGET_DIR:-} ]]; then
    CARGO_TARGET_DIR=$(realpath -m -- "$CARGO_TARGET_DIR")
    export CARGO_TARGET_DIR
fi
mato="${CARGO_TARGET_DIR:-$checkouts/mato/target}/release/mato"

case ${1:-} in
    prepare)
        data=$(realpath -e -- "${FLOCK_DATA_ROOT:-/media/nvme8tb/isla-gabriola}")
        mkdir -- "$job"
        cd -- "$job"
        cp -- "${MS2KG_ROOT:?}/flock/job.toml" .
        ln -s -- "${MS2KG_INPUT:?}" canonical-input
        ln -s -- "$checkouts" checkouts
        ln -s -- "$data/hocofaisan/references" references
        ln -s -- "$data/mato/wikidata" wikidata
        sha256sum --check --strict "$MS2KG_ROOT/flock/references.sha256"
        sha256sum wikidata/{taxa,chemicals}.sqlite > wikidata.sha256
        cd -- "$checkouts"
        for species in mato machaca peregrino cunaguaro picoto hocofaisan; do
            "${CARGO:-cargo}" build --locked --release --manifest-path "$species/Cargo.toml" --bin "$species" --target-dir "${CARGO_TARGET_DIR:-$checkouts/$species/target}"
        done
        "$mato" inspect --config "$job/job.toml"
        ;;
    run)
        exec "$mato" run --config "$job/job.toml"
        ;;
    *)
        echo 'Usage: bash flock/launch.sh prepare|run' >&2
        exit 2
        ;;
esac

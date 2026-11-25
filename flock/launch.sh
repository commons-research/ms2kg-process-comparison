#!/usr/bin/env bash
set -euo pipefail

job="${MS2KG_WORK:?}/flock"
checkouts=$(realpath -e -- "${FLOCK_ROOT:-${MS2KG_ROOT:?}/flock/upstream}")
# Mato resolves a relative target directory against its invocation directory.
if [[ -n ${CARGO_TARGET_DIR:-} ]]; then
    CARGO_TARGET_DIR=$(realpath -m -- "$CARGO_TARGET_DIR")
    export CARGO_TARGET_DIR
fi
mato="${CARGO_TARGET_DIR:-$checkouts/mato/target}/release/mato"

case ${1:-} in
    prepare)
        while read -r species revision upstream; do
            source_directory="$checkouts/$species"
            if [[ $(git -C "$source_directory" rev-parse HEAD) != "$revision" ]]; then
                echo "Expected $species at $revision in $source_directory" >&2
                exit 1
            fi
            expected_change=
            if [[ $species == hocofaisan ]]; then expected_change=src/main.rs; fi
            changes=$(git -C "$source_directory" diff --name-only --no-renames HEAD --)
            if [[ $changes != "$expected_change" ]]; then
                echo "Unexpected tracked source changes in $source_directory" >&2
                exit 1
            fi
        done < "${MS2KG_ROOT:?}/flock/sources.lock"
        data=$(realpath -e -- "${FLOCK_DATA_ROOT:-/media/nvme8tb/isla-gabriola}")
        mkdir -- "$job"
        cd -- "$job"
        cp -- "${MS2KG_ROOT:?}/flock/job.toml" .
        ln -s -- "${MS2KG_INPUT:?}" canonical-input
        ln -s -- "$checkouts" checkouts
        ln -s -- "$data/hocofaisan/references" references
        ln -s -- "$data/mato/wikidata" wikidata
        cp -- "$MS2KG_ROOT/flock/"{references.sha256,sources.lock} .
        sha256sum --check --strict references.sha256
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

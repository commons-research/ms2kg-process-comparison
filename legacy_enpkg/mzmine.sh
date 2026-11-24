#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077

fail() { printf '%s\n' "$*" >&2; exit 1; }

launcher=${MZMINE_BIN:-mzmine}
command -v "$launcher" >/dev/null || fail 'Install MZmine 4.11.0 or set MZMINE_BIN. See legacy_enpkg/MZMINE.md.'
version=$("$launcher" --version 2>&1)
[[ $version == *'Starting mzmine 4.11.0 '* ]] || fail 'Expected MZmine 4.11.0. See legacy_enpkg/MZMINE.md.'

if [[ -n ${MZMINE_LICENSE_FILE:-} ]]; then
  [[ -r $MZMINE_LICENSE_FILE ]] || fail 'Cannot read MZMINE_LICENSE_FILE.'
  credentials=(--user "$MZMINE_LICENSE_FILE")
else
  [[ -f .env ]] || fail 'Set the token in .env as described in legacy_enpkg/MZMINE.md.'
  source ./.env
  : "${MZMINE_CLI_TOKEN:?Set the token in .env as described in legacy_enpkg/MZMINE.md}"
  credentials=(--cli-token "$MZMINE_CLI_TOKEN")
  find "$HOME" -maxdepth 1 -type f -user "$(id -un)" -name 'mzmine_*.log*' -exec chmod go-rwx -- {} +
fi

work=${MS2KG_WORK:?Run make pipeline enpkg}
mkdir "$work/temp" "$work/output"
for spectrum in "${MS2KG_INPUT:?}/msdata/raw/"*.mzXML; do
  stem=$(basename "$spectrum" .mzXML)
  directory="$work/output/$stem"
  mkdir "$directory"
  printf 'Processing %s\n' "$stem"
  "$launcher" "${credentials[@]}" --batch "$1" \
    --input "$spectrum" --output "$directory/$stem" --temp "$work/temp" --threads "$2" \
    > "$directory/run.log" 2>&1 || fail "MZmine failed for $stem. Inspect $directory/run.log privately."
  for suffix in _iimn_fbmn.mgf _iimn_fbmn_quant.csv _sirius.mgf; do
    [[ -s $directory/$stem$suffix ]] || fail "Missing or empty export: $directory/$stem$suffix"
  done
done
printf 'MZmine exports: %s/output\n' "$work"

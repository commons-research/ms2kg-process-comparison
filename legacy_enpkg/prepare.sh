#!/usr/bin/env bash
set -euo pipefail
: "${MS2KG_ROOT:?missing benchmark repository}" "${MS2KG_INPUT:?missing canonical input}" "${MS2KG_WORK:?missing trial directory}" "${MS2KG_ARCHIVE:?missing verified toy release ZIP}"
export ENPKG_ROOT="$(realpath -e -- "${ENPKG_ROOT:-$MS2KG_ROOT/legacy_enpkg/upstream}")"
python="$ENPKG_ROOT/.venv/bin/python"
if [[ ! -x "$python" ]]; then
    echo "Missing $python. Install ENPKG's locked dependencies in its .venv with uv sync --frozen." >&2
    exit 1
fi
exec timeout --kill-after=10s 15m "$python" -I -B "$MS2KG_ROOT/legacy_enpkg/prepare.py"

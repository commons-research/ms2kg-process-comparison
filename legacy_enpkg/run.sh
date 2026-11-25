#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
shopt -s nullglob dotglob

fail() { printf '%s\n' "$*" >&2; exit 1; }
require_file() { [[ -f $1 && -s $1 ]] || fail "Missing or empty trial artifact $1"; }
require_graph() {
    require_file "$1"
    LC_ALL=C grep -qm1 '^[[:space:]]*[^@#[:space:]]' "$1" || fail "No RDF statements in $1"
}
stage() {
    printf 'Running ENPKG %s\n' "$1"
    timeout -k 30s 4h sh -e "workflow/$1.sh"
}

cd "${MS2KG_ROOT:?Run make compare}"
installation=$(realpath -e -- "${ENPKG_ROOT:-$MS2KG_ROOT/legacy_enpkg/upstream-fixed}")
work=${MS2KG_WORK:?}
trial=$work/enpkg
processed=$trial/data/input/enpkg_toy_dataset/msdata/processed
[[ -d $processed ]] || fail 'Missing prepared ENPKG input directory.'
existing=("$processed"/*)
((${#existing[@]} == 0)) || fail 'Expected an empty ENPKG processed input directory.'
raw_files=("${MS2KG_INPUT:?}/msdata/raw/"*.mzXML)
((${#raw_files[@]} == 6)) || fail 'Expected six canonical toy raw files.'

timeout -k 30s 4h bash legacy_enpkg/mzmine.sh legacy_enpkg/toy-unaligned.mzbatch 4
for spectrum in "${raw_files[@]}"; do
    stem=${spectrum##*/}
    stem=${stem%.mzXML}
    prefix=$work/output/$stem/$stem
    for suffix in _iimn_fbmn.mgf _iimn_fbmn_quant.csv _sirius.mgf; do
        require_file "$prefix$suffix"
        ln -- "$prefix$suffix" "$processed/"
    done
done

source "$installation/.venv/bin/activate"
[[ $VIRTUAL_ENV -ef $installation/.venv ]] || fail 'ENPKG activation selected a different environment.'
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$trial/src"
cd "$trial"
sample=VGF151_E05
analysis=data/output/individual_analysis
positive=$analysis/$sample/pos
stage 01_1_workflow_create_architecture
stage 02_workflow_massive_id
stage 03_workflow_taxo_enhancer
require_file "$analysis/$sample/taxo_output/${sample}_taxo_metadata.tsv"
stage 05_workflow_make_adducts
stage 06_workflow_annotate_mn_isdb
require_file "$positive/isdb/${sample}_isdb_reweighted_flat_pos.tsv"
require_file "$positive/molecular_network/${sample}_mn_pos.graphml"
printf 'Running SIRIUS with private log %s/sirius.log\n' "$work"
(
    if [[ -f $installation/.env ]]; then
        set -a
        source "$installation/.env"
        set +a
    fi
    : "${SIRIUS_USERNAME:?Missing SIRIUS_USERNAME}" "${SIRIUS_PASSWORD:?Missing SIRIUS_PASSWORD}"
    unset PATH_TO_SIRIUS
    stage 07_workflow_annotate_sirius
) >"$work/sirius.log" 2>&1
for summary in formula_identifications structure_identifications canopus_formula_summary; do
    require_file "$positive/${sample}_WORKSPACE_SIRIUS/$summary.tsv"
done
stage 08_workflow_chemo_info_fetcher
require_file sql_db/structures_metadata.db
stage 09_workflow_memo
require_file data/output/memo_matrix/memo_matrix.gz
stage 10_workflow_graph_builder

for fragment in metadata_module_enpkg features_pos features_spec2vec_pos sirius_pos canopus_pos isdb_pos individual_mn_pos structures_metadata; do
    require_graph "$analysis/$sample/rdf/$fragment.ttl"
done
for specimen in "$sample" VGF138_A01 VGF140_H12; do
    require_graph "$analysis/$specimen/rdf/metadata_enpkg.ttl"
    graphs=(data/output/standalone_graphs/"MSV000087728_${specimen}_merged_graph_"*.ttl)
    ((${#graphs[@]} == 1)) || fail "Expected one merged graph for $specimen."
    require_graph "${graphs[0]}"
done

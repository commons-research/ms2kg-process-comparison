"""Read final structure reports for ENPKG's positive-mode biological samples.

SIRIUS and ISDB summaries have no shared, unique candidate key. The filename
and one-based data-row number identify the assertion in its retained report,
including tied ranks and candidates without a chemical identifier.
"""

import csv
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from chemical_records import Candidate, Match
from legacy_enpkg.shared import _acquisition, _records


SIRIUS_COLUMNS = ('mappingFeatureId', 'structurePerIdRank', 'CSI:FingerIDScore', 'InChIkey2D', 'InChI', 'smiles', 'name', 'adduct')
SPECTRAL_COLUMNS = ('mappingFeatureId', 'spectralMatchRank', 'similarity', 'InChIkey2D', 'referenceSmiles', 'referenceName', 'referenceAdduct', 'referenceSplash', 'analogHit')
ISDB_COLUMNS = ('feature_id', 'rank_final', 'final_score', 'short_inchikey', 'structure_smiles_2D', 'adduct', 'libname')


def _rows(path, columns):
    with path.open(encoding='utf-8', newline='') as stream:
        try:
            reader = csv.DictReader(stream, delimiter='\t', strict=True)
            header = reader.fieldnames or []
            if len(set(header)) != len(header) or not set(columns).issubset(header):
                raise ValueError(f'Invalid ENPKG candidate columns in {path}')
            for number, row in enumerate(reader, 1):
                if None in row or None in row.values():
                    raise ValueError(f'Malformed ENPKG record {number} in {path}')
                yield number, row
        except csv.Error as error:
            raise ValueError(f'Malformed ENPKG table {path}') from error


def _matches(database):
    matches = defaultdict(list)
    if not database.exists():
        return matches
    query = 'SELECT short_inchikey, smiles, wikidata_id, inchikey, isomeric_smiles FROM structures_metadata'
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        for connectivity, smiles, entity, key, isomeric in connection.execute(query):
            if entity in (None, '', 'no_wikidata_match'):
                continue
            qid = re.fullmatch(r'https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)', entity)
            if not qid or not re.fullmatch('[A-Z]{14}-[A-Z]{10}-[A-Z]', key or '') or key[:14] != connectivity:
                raise ValueError(f'Invalid Wikidata structure record for {entity!r} in {database}')
            # ENPKG fills a missing Wikidata isomeric SMILES with its generic SMILES.
            sourced = isomeric if isomeric not in (None, smiles, 'no_wikidata_match', 'unknown') else ''
            matches[connectivity].append(Match(qid=qid[1], key=key, origin='ENPKG structure metadata', isomeric_smiles=sourced))
    return matches


def _candidate(path, number, filename, feature, method, key, references, evidence='', **properties):
    if not re.fullmatch('[1-9][0-9]*', feature):
        raise ValueError(f'Invalid native feature ID {feature!r} at {path} data row {number}')
    if key and not re.fullmatch('[A-Z]{14}', key):
        raise ValueError(f'Invalid connectivity key {key!r} at {path} data row {number}')
    identifier = f'{path.name}#{number}'
    return Candidate(filename=filename, feature=feature, method=method, identifier=identifier,
                     key=key, matches=tuple(references.get(key, ())), evidence=evidence or identifier, **properties)


def _sirius(path, filename, references, method):
    columns = SIRIUS_COLUMNS + (('pubchemids',) if method == 'sirius' else ())
    for number, row in _rows(path, columns):
        pubchem = row.get('pubchemids', '')
        if pubchem and not re.fullmatch(r'[1-9][0-9]*(?:;[1-9][0-9]*)*', pubchem):
            raise ValueError(f'Invalid PubChem identifier list {pubchem!r} at {path} data row {number}')
        yield _candidate(path, number, filename, row['mappingFeatureId'], method, row['InChIkey2D'], references,
                         rank=row['structurePerIdRank'], score=row['CSI:FingerIDScore'], inchi=row['InChI'],
                         smiles=row['smiles'], name=row['name'], adduct=row['adduct'], formula=row.get('molecularFormula', ''),
                         pubchem=tuple(pubchem.split(';')) if pubchem else ())


def _spectral(path, filename, references, method):
    for number, row in _rows(path, SPECTRAL_COLUMNS):
        analog = row['analogHit'].lower()
        if analog not in ('true', 'false'):
            raise ValueError(f'Invalid analogHit {analog!r} at {path} data row {number}')
        yield _candidate(path, number, filename, row['mappingFeatureId'], 'sirius-analog' if analog == 'true' else method,
                         row['InChIkey2D'], references, rank=row['spectralMatchRank'], score=row['similarity'],
                         name=row['referenceName'], adduct=row['referenceAdduct'], smiles=row['referenceSmiles'],
                         evidence=row['referenceSplash'])


def _isdb(path, filename, references):
    for number, row in _rows(path, ISDB_COLUMNS):
        yield _candidate(path, number, filename, row['feature_id'], 'isdb', row['short_inchikey'], references,
                         rank=row['rank_final'], score=row['final_score'], smiles=row['structure_smiles_2D'],
                         adduct=row['adduct'], evidence=row['libname'], formula=row.get('structure_molecular_formula', ''))


def read_candidates(trial: Path):
    """Yield every reported candidate row, including ties and unresolved structures."""
    native = trial / 'enpkg'
    references = _matches(native / 'sql_db/structures_metadata.db')
    analysis = native / 'data/output/individual_analysis'
    claimed = set()
    for directory in sorted(analysis.iterdir()):
        if not directory.is_dir():
            continue
        sample = directory.name
        metadata = directory / f'{sample}_metadata.tsv'
        rows = _records(metadata, ('sample_id', 'sample_type', 'sample_filename_pos'))
        if len(rows) != 1 or rows[0]['sample_id'] != sample:
            raise ValueError(f'Expected one sample matching its directory in {metadata}')
        if rows[0]['sample_type'] in ('blank', 'qc'):
            continue
        if rows[0]['sample_type'] != 'sample':
            raise ValueError(f'Unknown sample type in {metadata}')
        filename = _acquisition(trial / 'output', rows[0]['sample_filename_pos'])
        if filename in claimed:
            raise ValueError(f'Multiple samples claim {filename!r} in {analysis}')
        claimed.add(filename)
        positive = directory / 'pos'
        workspace = positive / f'{sample}_WORKSPACE_SIRIUS'
        yield from _sirius(workspace / 'structure_identifications.tsv', filename, references, 'sirius')
        for name, method, reader in [('denovo_structure_identifications.tsv', 'sirius-denovo', _sirius),
                                     ('spectral_matches.tsv', 'sirius-spectral', _spectral),
                                     ('spectral_matches_analog.tsv', 'sirius-analog', _spectral)]:
            path = workspace / name
            if path.exists():
                yield from reader(path, filename, references, method)
        yield from _isdb(positive / 'isdb' / f'{sample}_isdb_reweighted_flat_pos.tsv', filename, references)

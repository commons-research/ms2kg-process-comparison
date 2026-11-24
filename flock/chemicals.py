"""Read library hits and their separate structure references from a finalized Flock database."""

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from chemical_records import Candidate, Match


def _index_matches(database):
    identifiers = defaultdict(list)
    for key, qid, compound in database.execute('''
        SELECT inchikey, wikidata_qid, pubchem_cid FROM chemical_pubchem_ids
        ORDER BY inchikey, wikidata_qid, pubchem_cid
    '''):
        identifiers[key, qid].append(compound)
    matches = defaultdict(list)
    for key, qid, name in database.execute('''
        SELECT inchikey, wikidata_qid, name FROM chemical_entities ORDER BY inchikey, wikidata_qid
    '''):
        matches[key].append(Match(qid=qid, key=key, name=name or '', origin='Wikidata index',
                                  pubchem=tuple(identifiers.get((key, qid), ()))))
    return matches


def read_candidates(trial: Path):
    """Yield one candidate per native (run, feature, rank), regardless of reference coverage."""
    path = (trial / 'flock/toy.sqlite').resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as database:
        database.row_factory = sqlite3.Row
        incomplete = database.execute('''
            SELECT run_id, feature_id FROM annotation_features AS feature
            WHERE hit_count != (SELECT count(*) FROM annotation_hits AS hit
                                WHERE hit.run_id = feature.run_id AND hit.feature_id = feature.feature_id)
            LIMIT 1
        ''').fetchone()
        if incomplete:
            raise ValueError(f'Flock hit count disagrees with the saved candidates for {tuple(incomplete)}')
        indexed = _index_matches(database)
        for hit in database.execute('''
            SELECT hits.run_id, hits.feature_id, hits.rank, runs.filename, features.status, samples.sample_id,
                   hits.library_spectrum_id, hits.library_name, hits.library_inchikey, hits.library_headers_json,
                   hits.combined_score, hits.matched_lotus_inchikey, hits.matched_lotus_structure_wikidata
            FROM annotation_hits AS hits
            LEFT JOIN annotation_features AS features USING (run_id, feature_id)
            LEFT JOIN annotation_runs AS runs ON runs.id = hits.run_id
            LEFT JOIN spectrum_files AS files ON files.dataset_id = runs.dataset_id AND files.filename = runs.filename
            LEFT JOIN sample_rows AS samples ON samples.dataset_id = files.dataset_id AND samples.row_number = files.row_number
            ORDER BY hits.run_id, hits.feature_id, hits.rank
        '''):
            if hit['status'] != 'hits' or hit['sample_id'] is None:
                raise ValueError(f"Flock hit lacks its native feature or sample association at run {hit['run_id']}, feature {hit['feature_id']}")
            headers = json.loads(hit['library_headers_json'])
            key = hit['library_inchikey'] or headers.get('INCHIKEY', '')
            matches = indexed.get(key, ())
            lotus_key = hit['matched_lotus_inchikey']
            structure = hit['matched_lotus_structure_wikidata']
            if key and lotus_key and structure and key[:14] == lotus_key[:14]:
                qid = structure.removeprefix('http://www.wikidata.org/entity/').removeprefix('https://www.wikidata.org/entity/')
                matches = (*matches, Match(qid=qid, key=lotus_key, origin='LOTUS'))
            yield Candidate(filename=hit['filename'], feature=hit['feature_id'], method='flock',
                            identifier=f"{hit['run_id']}/{hit['rank']}", key=key, name=hit['library_name'],
                            inchi=headers.get('INCHI', ''), smiles=headers.get('SMILES', ''), adduct=headers.get('ADDUCT', ''),
                            formula=headers.get('MOLECULAR_FORMULA', ''),
                            rank=str(hit['rank']), score=str(hit['combined_score']), evidence=hit['library_spectrum_id'],
                            matches=tuple(matches))

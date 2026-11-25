import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, RDF, URIRef
from rdflib.compare import isomorphic

from shared_schema import export_trial


SAMPLES = [('VGF151_E05', 'sample', 'Datura stramonium'), ('VGF138_A01', 'qc', ''), ('VGF140_H12', 'blank', '')]
ROOT = Path(__file__).resolve().parent


def write_table(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(header)
        writer.writerows(rows)


def native_trial(trial):
    header = ['sample_id', 'sample_type', 'source_taxon', 'sample_filename_pos', 'sample_filename_neg']
    rows = [(*sample, f'{sample[0]}_pos.mzXML', f'{sample[0]}_neg.mzXML') for sample in SAMPLES]
    metadata = trial / 'metadata.tsv'
    write_table(metadata, header, rows)
    (trial / 'flock').mkdir()
    with sqlite3.connect(trial / 'flock/toy.sqlite') as store:
        store.executescript('''
            CREATE TABLE datasets (id INTEGER PRIMARY KEY);
            CREATE TABLE sample_rows (dataset_id, row_number, sample_id, attributes_json, taxon_id);
            CREATE TABLE spectrum_files (dataset_id, row_number, filename, column_name);
            CREATE TABLE taxa (id INTEGER PRIMARY KEY, name);
            CREATE TABLE taxon_resolutions (taxon_id INTEGER PRIMARY KEY, qid);
            INSERT INTO datasets VALUES (12);
            INSERT INTO taxa VALUES (7, 'Datura stramonium');
            INSERT INTO taxon_resolutions VALUES (7, 'Q30959');
        ''')
        for number, row in enumerate(rows, 1):
            identifier, role, name, positive, negative = row
            sample = trial / 'enpkg/data/output/individual_analysis' / identifier
            write_table(sample / f'{identifier}_metadata.tsv', header, [row])
            if name:
                write_table(sample / 'taxo_output' / f'{identifier}_taxo_metadata.tsv', ['sample_id', 'source_taxon', 'wd.value'], [(identifier, name.lower(), 'http://www.wikidata.org/entity/Q30959')])
            store.execute('INSERT INTO sample_rows VALUES (12, ?, ?, ?, ?)', (number, identifier, json.dumps(dict(zip(header, row))), 7 if name else None))
            for polarity, filename in [('pos', positive), ('neg', negative)]:
                store.execute('INSERT INTO spectrum_files VALUES (12, ?, ?, ?)', (number, filename, f'sample_filename_{polarity}'))
                stem = Path(filename).stem
                directory = trial / 'output' / stem
                directory.mkdir(parents=True)
                (directory / f'{stem}_iimn_fbmn_quant.csv').write_text(f'row ID,{filename} Peak area\n1,12\n')
    return metadata


class SharedExportTest(unittest.TestCase):
    def test_both_native_formats_export_the_reference_graph(self):
        expected = Graph().parse(ROOT / 'fixtures/toy-v2.ttl')
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            metadata = native_trial(trial)
            for pipeline in ('enpkg', 'flock'):
                with self.subTest(pipeline=pipeline):
                    emitted = export_trial(pipeline, trial, metadata)
                    self.assertTrue(isomorphic(expected, emitted), (expected - emitted, emitted - expected))
                    project = 'https://github.com/commons-research/ms2kg-process-comparison'
                    vocabulary = set(emitted.predicates()) | set(emitted.objects(None, RDF.type))
                    self.assertFalse({term for term in vocabulary if str(term).startswith(project)})

    def test_control_acquisition_with_no_detected_features_is_preserved(self):
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            metadata = native_trial(trial)
            stem = 'VGF140_H12_neg'
            table = trial / 'output' / stem / f'{stem}_iimn_fbmn_quant.csv'
            table.write_text(f'row ID,{stem}.mzXML Peak area\n')
            emitted = export_trial('enpkg', trial, metadata)
            self.assertTrue(isomorphic(Graph().parse(ROOT / 'fixtures/toy-v2.ttl'), emitted))

    def test_missing_native_acquisition_cannot_be_filled_from_input(self):
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            metadata = native_trial(trial)
            stem = 'VGF138_A01_neg'
            (trial / 'output' / stem / f'{stem}_iimn_fbmn_quant.csv').unlink()
            with sqlite3.connect(trial / 'flock/toy.sqlite') as store:
                store.execute('DELETE FROM spectrum_files WHERE filename = ?', (stem + '.mzXML',))
            for pipeline in ('enpkg', 'flock'):
                with self.subTest(pipeline=pipeline), self.assertRaises((ValueError, FileNotFoundError)):
                    export_trial(pipeline, trial, metadata)

    def test_unresolved_taxon_keeps_the_name_without_inventing_an_item(self):
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            metadata = native_trial(trial)
            sample = 'VGF151_E05'
            table = trial / 'enpkg/data/output/individual_analysis' / sample / 'taxo_output' / f'{sample}_taxo_metadata.tsv'
            write_table(table, ['sample_id', 'source_taxon', 'wd.value'], [(sample, 'datura stramonium', '')])
            with sqlite3.connect(trial / 'flock/toy.sqlite') as store:
                store.execute('DELETE FROM taxon_resolutions')
            expected = Graph().parse(ROOT / 'fixtures/toy-v2.ttl')
            expected.remove((None, URIRef('http://rs.tdwg.org/dwc/iri/toTaxon'), URIRef('http://www.wikidata.org/entity/Q30959')))
            for pipeline in ('enpkg', 'flock'):
                with self.subTest(pipeline=pipeline):
                    self.assertTrue(isomorphic(expected, export_trial(pipeline, trial, metadata)))

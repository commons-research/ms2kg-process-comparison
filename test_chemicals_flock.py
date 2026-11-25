import sqlite3
import tempfile
import unittest
from pathlib import Path

from rdflib import Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDFS, SOSA, XSD

from chemical_schema import export_chemicals, inventory
from test_chemical_schema import HAS_ATTRIBUTE, SCHEMA, assert_external_vocabulary, property_values


HOCOFAISAN = URIRef('https://github.com/oolonek/hocofaisan')
ANNOTATION = URIRef(f'{HOCOFAISAN}/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/TECHNICAL.md#reference-preparation-and-annotation')
WIKIDATA = Namespace('http://www.wikidata.org/entity/')
DIRECT = Namespace('http://www.wikidata.org/prop/direct/')
FILES = Namespace('https://github.com/commons-research/ms2kg-process-comparison#10018590/file/')


def flock_fixture(trial):
    (trial / 'flock').mkdir()
    with sqlite3.connect(trial / 'flock/toy.sqlite') as store:
        store.executescript('''
            CREATE TABLE datasets (id INTEGER PRIMARY KEY);
            CREATE TABLE sample_rows (dataset_id, row_number, sample_id, attributes_json, taxon_id);
            CREATE TABLE spectrum_files (dataset_id, row_number, filename, column_name);
            CREATE TABLE taxa (id INTEGER PRIMARY KEY, name);
            CREATE TABLE taxon_resolutions (taxon_id INTEGER PRIMARY KEY, qid);
            CREATE TABLE annotation_runs (id INTEGER PRIMARY KEY, dataset_id, filename, status);
            CREATE TABLE annotation_features (run_id, feature_id, hit_count, status, PRIMARY KEY(run_id, feature_id));
            CREATE TABLE annotation_hits (run_id, feature_id, rank, library_spectrum_id, library_name, library_inchikey,
                library_headers_json, spectral_score, combined_score, matched_short_inchikey, matched_lotus_inchikey,
                matched_lotus_structure_wikidata, PRIMARY KEY(run_id, feature_id, rank));
            CREATE TABLE chemical_lookups (inchikey PRIMARY KEY, status);
            CREATE TABLE chemical_entities (inchikey, wikidata_qid, name, PRIMARY KEY(inchikey, wikidata_qid));
            CREATE TABLE chemical_pubchem_ids (inchikey, wikidata_qid, pubchem_cid, PRIMARY KEY(inchikey, wikidata_qid, pubchem_cid));
            INSERT INTO datasets VALUES (2);
            INSERT INTO sample_rows VALUES (2, 1, 'VGF151_E05', '{"sample_type":"sample","source_taxon":""}', NULL),
                (2, 2, 'VGF138_A01', '{"sample_type":"qc","source_taxon":""}', NULL);
            INSERT INTO spectrum_files VALUES (2, 1, 'VGF151_E05_pos.mzXML', 'sample_filename_pos'),
                (2, 2, 'VGF138_A01_pos.mzXML', 'sample_filename_pos');
            INSERT INTO annotation_runs VALUES (9, 2, 'VGF151_E05_pos.mzXML', 'hits'), (4, 2, 'VGF138_A01_pos.mzXML', 'hits');
            INSERT INTO annotation_features VALUES (9, '1', 2, 'hits'), (4, '1', 1, 'hits'), (9, '2', 0, 'no_hits');
            INSERT INTO annotation_hits VALUES
                (9, '1', 1, 'spectrum-77', 'serine', 'MTCFGRXMJLQNBG-UHFFFAOYSA-N',
                 '{"SMILES":"NC(CO)C(O)=O","INCHI":"InChI=1S/C3H7NO3/c4-2(1-5)3(6)7/h2,5H,1,4H2,(H,6,7)","MOLECULAR_FORMULA":"C3H7NO3","ADDUCT":"[M+H]+"}',
                 0.31, 1.31, 'MTCFGRXMJLQNBG', 'MTCFGRXMJLQNBG-REOHCLBHSA-N', 'http://www.wikidata.org/entity/Q103'),
                (9, '1', 2, 'spectrum-80', 'unresolved', 'MTCFGRXMJLQNBG-UWTATZPHSA-N', '{}', 0.2, 0.2,
                 'QNAYBMKLOCPYGJ', 'QNAYBMKLOCPYGJ-REOHCLBHSA-N', 'http://www.wikidata.org/entity/Q104'),
                (4, '1', 1, 'spectrum-14', 'partial', 'QNAYBMKLOCPYGJ', '{}', 0.1, 1.1, 'QNAYBMKLOCPYGJ',
                 'QNAYBMKLOCPYGJ-REOHCLBHSA-N', 'http://www.wikidata.org/entity/Q104');
            INSERT INTO chemical_lookups VALUES ('MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'ambiguous'), ('MTCFGRXMJLQNBG-UWTATZPHSA-N', 'not_found');
            INSERT INTO chemical_entities VALUES ('MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'Q101', 'Index label one'),
                ('MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'Q102', 'Index label two');
            INSERT INTO chemical_pubchem_ids VALUES ('MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'Q101', '20001'),
                ('MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'Q101', '20002');
        ''')


class FlockChemicalExportTest(unittest.TestCase):
    def test_library_hits_keep_native_structures_and_distinguish_lotus_from_exact_index_matches(self):
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            flock_fixture(trial)
            graph = export_chemicals('flock', trial)
        assert_external_vocabulary(self, graph)
        observations = set(graph.subjects(RDF.type, SOSA.Observation))
        self.assertEqual(len(observations), 3)
        results = {graph.value(observation, SOSA.hasResult, any=False) for observation in observations}
        self.assertEqual(len(results), 3)

        matched, = results.intersection(graph.subjects(DIRECT.P235, Literal('MTCFGRXMJLQNBG-UHFFFAOYSA-N')))
        self.assertEqual(set(graph.objects(matched, PROV.wasDerivedFrom / RDFS.seeAlso)), {WIKIDATA.Q101, WIKIDATA.Q102, WIKIDATA.Q103})
        self.assertEqual(inventory(graph), (3, 2, {
            'full InChIKeys': {'MTCFGRXMJLQNBG-UHFFFAOYSA-N', 'MTCFGRXMJLQNBG-UWTATZPHSA-N'},
            'connectivity blocks': {'MTCFGRXMJLQNBG', 'QNAYBMKLOCPYGJ'},
            'full-key Wikidata items': {WIKIDATA.Q101, WIKIDATA.Q102}, 'other Wikidata associations': {WIKIDATA.Q103, WIKIDATA.Q104},
        }))
        self.assertIn((matched, DIRECT.P234, Literal('InChI=1S/C3H7NO3/c4-2(1-5)3(6)7/h2,5H,1,4H2,(H,6,7)')), graph)
        self.assertIn((matched, SCHEMA.smiles, Literal('NC(CO)C(O)=O')), graph)
        self.assertEqual(set(graph.objects(matched, RDFS.label)), {Literal('serine')})
        self.assertIn((matched, DIRECT.P274, Literal('C3H7NO3')), graph)
        self.assertFalse(list(graph.objects(matched, DIRECT.P233)))
        self.assertFalse(list(graph.objects(matched, DIRECT.P2017)))
        records = set(graph.objects(matched, PROV.wasDerivedFrom))
        indexed, = records.intersection(graph.subjects(RDFS.seeAlso, WIKIDATA.Q101))
        self.assertEqual({str(value) for value in graph.objects(indexed, DIRECT.P662)}, {'20001', '20002'})
        self.assertIn((indexed, RDFS.label, Literal('Index label one')), graph)
        other, = records.intersection(graph.subjects(RDFS.seeAlso, WIKIDATA.Q102))
        self.assertFalse(list(graph.objects(other, DIRECT.P662)))
        lotus, = records.intersection(graph.subjects(RDFS.seeAlso, WIKIDATA.Q103))
        self.assertIn((lotus, DIRECT.P235, Literal('MTCFGRXMJLQNBG-REOHCLBHSA-N')), graph)

        unresolved, = results.intersection(graph.subjects(DIRECT.P235, Literal('MTCFGRXMJLQNBG-UWTATZPHSA-N')))
        self.assertFalse(list(graph.objects(unresolved, PROV.wasDerivedFrom)))

        partial, = (result for result in results if property_values(graph, result, SCHEMA.identifier, 'InChIKey connectivity block') == [Literal('QNAYBMKLOCPYGJ')])
        self.assertFalse(list(graph.objects(partial, DIRECT.P235)))
        self.assertEqual(set(graph.objects(partial, PROV.wasDerivedFrom / RDFS.seeAlso)), {WIKIDATA.Q104})
        self.assertFalse(list(graph.triples((None, OWL.sameAs, None))))

        observation, = graph.subjects(SOSA.hasResult, matched)
        self.assertIn((observation, DCTERMS.source, Literal('spectrum-77')), graph)
        self.assertEqual(graph.value(observation, SOSA.usedProcedure, any=False), ANNOTATION)
        self.assertEqual(graph.value(observation, PROV.used, any=False), HOCOFAISAN)
        self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'combined_score'), [Literal('1.31', datatype=XSD.decimal)])
        self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'rank'), [Literal('1.0', datatype=XSD.decimal)])
        self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'ADDUCT'), [Literal('[M+H]+')])
        feature, = graph.objects(observation, SOSA.hasFeatureOfInterest)
        self.assertIn((feature, DCTERMS.identifier, Literal('1')), graph)
        self.assertIn((feature, PROV.wasDerivedFrom, FILES['VGF151_E05_pos.mzXML']), graph)
        unresolved_observation, = graph.subjects(SOSA.hasResult, unresolved)
        self.assertIn((unresolved_observation, SOSA.hasFeatureOfInterest, feature), graph)
        partial_observation, = graph.subjects(SOSA.hasResult, partial)
        partial_feature, = graph.objects(partial_observation, SOSA.hasFeatureOfInterest)
        self.assertNotEqual(feature, partial_feature)
        self.assertIn((partial_feature, PROV.wasDerivedFrom, FILES['VGF138_A01_pos.mzXML']), graph)

    def test_missing_reported_hit_fails_instead_of_exporting_partial_inventory(self):
        with tempfile.TemporaryDirectory() as scratch:
            trial = Path(scratch)
            flock_fixture(trial)
            with sqlite3.connect(trial / 'flock/toy.sqlite') as store:
                store.execute('DELETE FROM annotation_hits WHERE run_id = 9 AND rank = 2')
            with self.assertRaisesRegex(ValueError, 'hit count'):
                export_chemicals('flock', trial)

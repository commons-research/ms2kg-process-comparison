import sqlite3
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, PROV, RDFS, SOSA, XSD

from chemical_schema import export_chemicals, inventory
from test_chemical_schema import HAS_ATTRIBUTE, SCHEMA, assert_external_vocabulary, property_values
from test_shared_schema import native_trial, write_table


SIRIUS = Namespace('https://v6.docs.sirius-ms.io/methods-background/#')
SEARCH_MODE = Namespace('https://github.com/sirius-ms/sirius/blob/v6.5.4/sirius-sdk/sirius-sdk.openapi/docs/SpectralMatchType.md#')
ENPKG = URIRef('https://github.com/enpkg/enpkg_full')
REWEIGHTING = URIRef(f'{ENPKG}/blob/a6535a5dfda9f4c59c79f39401359cb14c521a86/03_enpkg_mn_isdb_isdb_taxo/README.md')
WD = Namespace('http://www.wikidata.org/entity/')
WDT = Namespace('http://www.wikidata.org/prop/direct/')
SAMPLE = 'VGF151_E05'
SIRIUS_HEADER = ['mappingFeatureId', 'structurePerIdRank', 'CSI:FingerIDScore', 'InChIkey2D', 'InChI', 'smiles', 'name', 'adduct', 'molecularFormula', 'pubchemids']
ISDB_HEADER = ['', 'feature_id', 'rank_final', 'final_score', 'libname', 'short_inchikey', 'structure_smiles_2D', 'adduct', 'structure_molecular_formula']


def chemical_trial(trial):
    native_trial(trial)
    positive = trial / 'enpkg/data/output/individual_analysis' / SAMPLE / 'pos'
    sirius = positive / f'{SAMPLE}_WORKSPACE_SIRIUS/structure_identifications.tsv'
    isdb = positive / 'isdb' / f'{SAMPLE}_isdb_reweighted_flat_pos.tsv'
    write_table(sirius, SIRIUS_HEADER, [
        ['1', '1', '-17.1', 'JVTAAEKCZFNVCJ', 'InChI=1S/C4H10O/c1-3-4(2)5/h4-5H,3H2,1-2H3', 'CCC(C)O', '2-butanol', '[M + H]+', 'C4H10O', '6568'],
        ['1', '2', '-25.6', '', '', 'CCOCC', 'diethyl ether', '[M + H]+', 'C4H10O', ''],
    ])
    write_table(isdb, ISDB_HEADER, [
        ['804', '1', '1', '9.5', 'MS1_match', 'JVTAAEKCZFNVCJ', 'CCC(C)O', 'pos_1_1proton', 'C4H10O'],
        ['603', '1', '1', '9.5', 'ISDB', 'LFQSCWFLJHTTHZ', 'CCO', '', 'C2H6O'],
    ])
    metadata = trial / 'enpkg/sql_db/structures_metadata.db'
    metadata.parent.mkdir()
    with sqlite3.connect(metadata) as connection:
        connection.execute('CREATE TABLE structures_metadata (short_inchikey, smiles, wikidata_id, inchikey, isomeric_smiles)')
        connection.executemany('INSERT INTO structures_metadata VALUES (?, ?, ?, ?, ?)', [
            ('JVTAAEKCZFNVCJ', 'CCC(C)O', 'http://www.wikidata.org/entity/Q101', 'JVTAAEKCZFNVCJ-BYPYZUCNSA-N', 'CC[C@H](C)O'),
            ('JVTAAEKCZFNVCJ', 'CCC(C)O', 'http://www.wikidata.org/entity/Q102', 'JVTAAEKCZFNVCJ-SCSAIBSYSA-N', 'CCC(C)O'),
            ('LFQSCWFLJHTTHZ', 'CCO', 'no_wikidata_match', 'LFQSCWFLJHTTHZ', 'CCO'),
        ])
    return sirius, isdb, metadata


class EnpkgChemicalTest(unittest.TestCase):
    def test_final_candidate_rows_preserve_ties_connectivity_only_matches_and_unresolved_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = Path(directory)
            chemical_trial(trial)
            graph = export_chemicals('enpkg', trial)
            self.assertTrue(isomorphic(graph, Graph().parse(trial / 'chemicals-v2.ttl')))
            assert_external_vocabulary(self, graph)
            observations = set(graph.subjects(RDF.type, SOSA.Observation))
            self.assertEqual(len(observations), 4)
            results = {graph.value(observation, SOSA.hasResult, any=False) for observation in observations}
            self.assertEqual(len(results), 4)
            features = {graph.value(observation, SOSA.hasFeatureOfInterest, any=False) for observation in observations}
            self.assertEqual(len(features), 1)
            self.assertEqual(len({graph.value(observation, SOSA.usedProcedure, any=False) for observation in observations}), 2)
            expected = {
                'structure_identifications.tsv#1': ('structurePerIdRank', '1.0', 'CSI:FingerIDScore', '-17.1', '[M + H]+'),
                'structure_identifications.tsv#2': ('structurePerIdRank', '2.0', 'CSI:FingerIDScore', '-25.6', '[M + H]+'),
                f'{SAMPLE}_isdb_reweighted_flat_pos.tsv#1': ('rank_final', '1.0', 'final_score', '9.5', 'pos_1_1proton'),
                f'{SAMPLE}_isdb_reweighted_flat_pos.tsv#2': ('rank_final', '1.0', 'final_score', '9.5', ''),
            }
            for observation in observations:
                identifier = str(graph.value(observation, DCTERMS.identifier, any=False))
                rank_name, rank, score_name, score, adduct = expected.pop(identifier)
                self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, rank_name), [Literal(rank, datatype=XSD.decimal)])
                self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, score_name), [Literal(score, datatype=XSD.decimal)])
                self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'adduct'), [Literal(adduct)] if adduct else [])
            self.assertFalse(expected)
            self.assertTrue(any('MS1_match' in str(graph.value(observation, DCTERMS.source)) for observation in observations))
            ambiguous = {result for result in results if property_values(graph, result, SCHEMA.identifier, 'InChIKey connectivity block') == [Literal('JVTAAEKCZFNVCJ')]}
            self.assertEqual(len(ambiguous), 2)
            for result in ambiguous:
                self.assertEqual(set(graph.objects(result, PROV.wasDerivedFrom / RDFS.seeAlso)), {WD.Q101, WD.Q102})
                self.assertIn((result, SCHEMA.smiles, Literal('CCC(C)O')), graph)
                self.assertFalse(list(graph.objects(result, WDT.P235)))
            self.assertEqual(inventory(graph), (4, 2, {
                'full InChIKeys': set(), 'connectivity blocks': {'JVTAAEKCZFNVCJ', 'LFQSCWFLJHTTHZ'},
                'full-key Wikidata items': set(), 'other Wikidata associations': {WD.Q101, WD.Q102},
            }))
            for result in ambiguous:
                records = set(graph.objects(result, PROV.wasDerivedFrom))
                first, = records & set(graph.subjects(RDFS.seeAlso, WD.Q101))
                second, = records & set(graph.subjects(RDFS.seeAlso, WD.Q102))
                self.assertIn((first, WDT.P2017, Literal('CC[C@H](C)O')), graph)
                self.assertFalse(list(graph.objects(second, WDT.P2017)))
            butanol, = set(graph.subjects(WDT.P234, Literal('InChI=1S/C4H10O/c1-3-4(2)5/h4-5H,3H2,1-2H3'))) & results
            self.assertIn((butanol, WDT.P662, Literal('6568')), graph)
            self.assertEqual(len(set(graph.subjects(WDT.P274, Literal('C4H10O'))) & results), 3)
            for smiles in ['CCOCC', 'CCO']:
                unresolved, = set(graph.subjects(SCHEMA.smiles, Literal(smiles))) & results
                self.assertFalse(list(graph.objects(unresolved, PROV.wasDerivedFrom)))

    def test_without_native_reference_database_all_candidates_remain_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = Path(directory)
            _, _, metadata = chemical_trial(trial)
            metadata.unlink()
            graph = export_chemicals('enpkg', trial)
            self.assertEqual(len(set(graph.subjects(RDF.type, SOSA.Observation))), 4)
            self.assertEqual(inventory(graph)[1], 0)

    def test_optional_sirius_reports_keep_de_novo_and_spectral_references_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = Path(directory)
            sirius, _, _ = chemical_trial(trial)
            write_table(sirius.with_name('denovo_structure_identifications.tsv'), SIRIUS_HEADER[:-1], [
                ['1', '3', '-11', 'LFQSCWFLJHTTHZ', '', 'CCO', '', '[M + H]+', 'C2H6O'],
            ])
            header = ['mappingFeatureId', 'spectralMatchRank', 'similarity', 'referenceAdduct', 'referenceSmiles', 'referenceName', 'referenceSplash', 'InChIkey2D', 'analogHit']
            for suffix, analog in [('', 'false'), ('_analog', 'true')]:
                write_table(sirius.with_name(f'spectral_matches{suffix}.tsv'), header, [
                    ['1', '1', '0.8', '[M + H]+', 'CCO', 'ethanol', 'splash10-0002-0900000000-example', 'LFQSCWFLJHTTHZ', analog],
                ])
            graph = export_chemicals('enpkg', trial)
            observations = set(graph.subjects(RDF.type, SOSA.Observation))
            self.assertEqual(len(observations), 7)
            procedures = {
                'structure_identifications.tsv': SIRIUS.CSIFingerID,
                'denovo_structure_identifications.tsv': SIRIUS.MSNovelist,
                'spectral_matches.tsv': SEARCH_MODE.L8,
                'spectral_matches_analog.tsv': SEARCH_MODE.L10,
                f'{SAMPLE}_isdb_reweighted_flat_pos.tsv': REWEIGHTING,
            }
            for observation in observations:
                report = str(graph.value(observation, DCTERMS.identifier, any=False)).split('#')[0]
                self.assertEqual(graph.value(observation, SOSA.usedProcedure, any=False), procedures[report])
                self.assertEqual(graph.value(observation, PROV.used, any=False), ENPKG if procedures[report] == REWEIGHTING else WD.Q124358188)
                if report.startswith('spectral_matches'):
                    self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'spectralMatchRank'), [Literal('1.0', datatype=XSD.decimal)])
                    self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'similarity'), [Literal('0.8', datatype=XSD.decimal)])
                    self.assertEqual(property_values(graph, observation, HAS_ATTRIBUTE, 'referenceAdduct'), [Literal('[M + H]+')])
            assert_external_vocabulary(self, graph)
            self.assertEqual(len(set(graph.subjects(SCHEMA.smiles, Literal('CCO')))), 4)

    def test_invalid_native_evidence_rejects_the_export(self):
        for problem in ['missing table', 'wrong header', 'missing feature', 'invalid PubChem CID']:
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as directory:
                trial = Path(directory)
                sirius, isdb, _ = chemical_trial(trial)
                if problem == 'missing table':
                    sirius.unlink()
                elif problem == 'wrong header':
                    write_table(isdb, ['feature_id', 'rank_final'], [['1', '1']])
                elif problem == 'invalid PubChem CID':
                    write_table(sirius, SIRIUS_HEADER, [['1', '1', '-17', '', '', 'CCO', '', '[M + H]+', 'C2H6O', 'unknown']])
                else:
                    write_table(isdb, ISDB_HEADER, [['4', '', '1', '9.5', 'ISDB', '', 'CCO', '', 'C2H6O']])
                with self.assertRaises((FileNotFoundError, ValueError)):
                    export_chemicals('enpkg', trial)
                self.assertFalse((trial / 'chemicals-v2.ttl').exists())

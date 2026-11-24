import unittest

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SOSA

from chemical_records import Candidate, Match
from chemical_schema import chemical_graph, inventory


SCHEMA = Namespace('https://schema.org/')
HAS_ATTRIBUTE = URIRef('http://semanticscience.org/resource/SIO_000008')
DIRECT = Namespace('http://www.wikidata.org/prop/direct/')
WIKIDATA = Namespace('http://www.wikidata.org/entity/')


def property_values(graph, subject, predicate, name):
    return [value for node in graph.objects(subject, predicate)
            if (node, RDF.type, SCHEMA.PropertyValue) in graph and (node, SCHEMA.propertyID, Literal(name)) in graph
            for value in graph.objects(node, SCHEMA.value)]


def assert_external_vocabulary(test, graph):
    project = 'https://github.com/commons-research/ms2kg-process-comparison'
    for term in (*graph.predicates(), *graph.objects(None, RDF.type), *graph.objects(None, SOSA.usedProcedure)):
        test.assertFalse(str(term).startswith(project), term)


class ChemicalGraphTest(unittest.TestCase):
    def test_full_and_connectivity_evidence_stay_distinct(self):
        source = Candidate(filename='VGF151_E05_pos.mzXML', feature='1', method='flock', identifier='1', key='QNAYBMKLOCPYGJ-REOHCLBHSA-N', inchi='InChI=1S/C3H7NO2', smiles='CC(N)C(O)=O', rank='1', score='0.63', matches=(
            Match('Q218642', 'QNAYBMKLOCPYGJ-REOHCLBHSA-N', 'Wikidata index'),
            Match('Q236975', 'QNAYBMKLOCPYGJ-UWTATZPHSA-N', 'LOTUS'),
            Match('Q105', '', 'reported association without key'),
        ))
        graph = chemical_graph('flock', [source])
        observation, = graph.subjects(RDF.type, SOSA.Observation)
        result, = graph.objects(observation, SOSA.hasResult)
        references = {(item, graph.value(record, DIRECT.P235), graph.value(record, DCTERMS.source))
                      for record in graph.objects(result, PROV.wasDerivedFrom) for item in graph.objects(record, RDFS.seeAlso)}
        self.assertEqual(references, {
            (WIKIDATA.Q218642, Literal(source.key), Literal('Wikidata index')),
            (WIKIDATA.Q236975, Literal('QNAYBMKLOCPYGJ-UWTATZPHSA-N'), Literal('LOTUS')),
            (WIKIDATA.Q105, None, Literal('reported association without key')),
        })
        self.assertEqual(inventory(graph), (1, 1, {
            'full InChIKeys': {source.key}, 'connectivity blocks': {'QNAYBMKLOCPYGJ'},
            'full-key Wikidata items': {WIKIDATA.Q218642}, 'other Wikidata associations': {WIKIDATA.Q236975, WIKIDATA.Q105},
        }))
        self.assertEqual(set(graph.objects(result, DIRECT.P235)), {Literal(source.key)})
        self.assertIn((result, DIRECT.P234, Literal(source.inchi)), graph)
        self.assertIn((result, SCHEMA.smiles, Literal(source.smiles)), graph)
        self.assertFalse(any(graph.triples((result, DIRECT.P233, None))))
        self.assertFalse(any(graph.triples((None, OWL.sameAs, None))))
        feature, = graph.objects(observation, SOSA.hasFeatureOfInterest)
        raw = URIRef('https://github.com/commons-research/ms2kg-process-comparison#10018590/file/VGF151_E05_pos.mzXML')
        self.assertIn((feature, PROV.wasDerivedFrom, raw), graph)
        assert_external_vocabulary(self, graph)

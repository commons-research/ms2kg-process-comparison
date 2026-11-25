"""Conformance examples for a third pipeline that uses no benchmark instance identifiers."""

import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDFS, SOSA

from schema.validate import validate_graph


EXAMPLE = Namespace('urn:third:')
DIRECT = Namespace('http://www.wikidata.org/prop/direct/')
DWCIRI = Namespace('http://rs.tdwg.org/dwc/iri/')
SHAPES = Path(__file__).resolve().parent / 'schema/shapes-v2.ttl'
TRIAL = '''
@prefix : <urn:third:> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dwc: <http://rs.tdwg.org/dwc/terms/> .
@prefix dwciri: <http://rs.tdwg.org/dwc/iri/> .
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sdo: <https://schema.org/> .
@prefix sio: <http://semanticscience.org/resource/> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix wd: <http://www.wikidata.org/entity/> .
:extract a prov:Entity, sosa:Sample ; dct:identifier "extract-17" ; dct:type "sample" ; prov:wasDerivedFrom :source .
:identification a dwc:Identification ; dct:subject :source ; dwc:verbatimIdentification "unresolved plant" .
:acquisition a obo:OBI_0003097, prov:Activity ; prov:used :extract ; dct:relation :raw ; sio:SIO_000008 :polarity .
:polarity a obo:MS_1000130 .
:raw a prov:Entity, sdo:MediaObject ; sdo:name "different.mzML" ; sdo:sha256 "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" .
:feature dct:identifier "peak-3" ; prov:wasDerivedFrom :raw .
:call a sosa:Observation ; dct:identifier "hit-1" ; sosa:hasFeatureOfInterest :feature ; sosa:observedProperty wd:Q500256 ; sosa:usedProcedure :method ; prov:used :software ; sosa:hasResult :candidate .
:candidate a sosa:Result .
'''


class SharedProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes = Graph().parse(SHAPES)

    def test_unresolved_identity_and_unfamiliar_method_are_valid(self):
        validate_graph(Graph().parse(data=TRIAL, format='turtle'), self.shapes)

    def test_broken_annotation_paths_and_identity_claims_are_rejected(self):
        for change in (
            lambda graph: graph.remove((EXAMPLE.call, SOSA.usedProcedure, None)),
            lambda graph: graph.set((EXAMPLE.feature, PROV.wasDerivedFrom, EXAMPLE.unmeasured)),
            lambda graph: graph.remove((EXAMPLE.acquisition, DCTERMS.relation, None)),
            lambda graph: graph.add((EXAMPLE.identification, DWCIRI.toTaxon, Literal('Q42'))),
            lambda graph: graph.add((EXAMPLE.candidate, DIRECT.P235, Literal('ABCDEFGHIJKLMN'))),
            lambda graph: graph.add((EXAMPLE.candidate, PROV.wasDerivedFrom, EXAMPLE.unsourced)),
        ):
            graph = Graph().parse(data=TRIAL, format='turtle')
            change(graph)
            with self.subTest(line=change.__code__.co_firstlineno), self.assertRaisesRegex(ValueError, 'Constraint Violation'):
                validate_graph(graph, self.shapes)

    def test_an_unrelated_graph_does_not_pass_without_a_target(self):
        graph = Graph().add((EXAMPLE.note, RDFS.seeAlso, URIRef('urn:other:note')))
        with self.assertRaisesRegex(ValueError, 'The trial must contain at least one LC-MS acquisition'):
            validate_graph(graph, self.shapes)

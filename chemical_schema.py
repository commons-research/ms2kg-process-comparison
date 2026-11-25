"""Map native structure hypotheses without asserting compounds are present in a sample."""

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, PROV, SDO, SOSA, XSD

from benchmark_input import INPUT_DIGESTS
from flock.chemicals import read_candidates as read_flock
from legacy_enpkg.chemicals import read_candidates as read_enpkg
from shared_terms import FILES, WIKIDATA


SIO = Namespace('http://semanticscience.org/resource/')
DIRECT = Namespace('http://www.wikidata.org/prop/direct/')
KEY = re.compile(r'[A-Z]{14}(?:-[A-Z]{10}-[A-Z])?')
CONNECTIVITY_SCHEME = Literal('InChIKey connectivity block')
SIRIUS = Namespace('https://v6.docs.sirius-ms.io/methods-background/#')
SPECTRAL_MODES = Namespace('https://github.com/sirius-ms/sirius/blob/v6.5.4/sirius-sdk/sirius-sdk.openapi/docs/SpectralMatchType.md#')
ENPKG = URIRef('https://github.com/enpkg/enpkg_full')
HOCOFAISAN = URIRef('https://github.com/oolonek/hocofaisan')
STRUCTURE_FIELDS = ('structurePerIdRank', 'CSI:FingerIDScore', 'adduct')
SPECTRAL_FIELDS = ('spectralMatchRank', 'similarity', 'referenceAdduct')
METHODS = {
    'sirius': (SIRIUS.CSIFingerID, WIKIDATA.Q124358188, STRUCTURE_FIELDS),
    'sirius-denovo': (SIRIUS.MSNovelist, WIKIDATA.Q124358188, STRUCTURE_FIELDS),
    'sirius-spectral': (SPECTRAL_MODES.L8, WIKIDATA.Q124358188, SPECTRAL_FIELDS),
    'sirius-analog': (SPECTRAL_MODES.L10, WIKIDATA.Q124358188, SPECTRAL_FIELDS),
    'isdb': (URIRef(f'{ENPKG}/blob/53aff82d01be6856cfd12a9910ddb9fff93dc0bd/03_enpkg_mn_isdb_isdb_taxo/README.md'),
             ENPKG, ('rank_final', 'final_score', 'adduct')),
    'flock': (URIRef(f'{HOCOFAISAN}/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/TECHNICAL.md#reference-preparation-and-annotation'),
              HOCOFAISAN, ('rank', 'combined_score', 'ADDUCT')),
}


def _add_property_value(graph, subject, predicate, field, value):
    node = BNode()
    graph.add((subject, predicate, node))
    graph.add((node, RDF.type, SDO.PropertyValue))
    graph.add((node, SDO.propertyID, field))
    graph.add((node, SDO.value, value))


def add_key(graph, subject, key):
    if key:
        if not KEY.fullmatch(key):
            raise ValueError(f'Invalid reported InChIKey or connectivity block {key!r}')
        if len(key) == 27:
            graph.add((subject, DIRECT.P235, Literal(key)))
        else:
            _add_property_value(graph, subject, SDO.identifier, CONNECTIVITY_SCHEME, Literal(key))


def add_number(graph, subject, field, value):
    if value != '':
        try:
            number = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError(f'Invalid {field} value {value!r}') from error
        if not number.is_finite():
            raise ValueError(f'Nonfinite {field} value {value!r}')
        lexical = format(number, 'f')
        decimal = Literal(lexical if '.' in lexical else lexical + '.0', datatype=XSD.decimal)
        _add_property_value(graph, subject, SIO.SIO_000008, Literal(field), decimal)


def chemical_graph(pipeline, candidates):
    graph = Graph()
    for prefix, namespace in [('sio', SIO), ('schema', SDO), ('wdt', DIRECT), ('wd', WIKIDATA), ('file', FILES)]:
        graph.bind(prefix, namespace)
    features = {}
    references = {}
    identifiers = set()
    for candidate in candidates:
        feature_key = candidate.filename, candidate.feature
        identity = (*feature_key, candidate.method, candidate.identifier)
        if not all(identity) or identity in identifiers:
            raise ValueError(f'Missing or duplicate {pipeline} candidate identity {identity!r}')
        identifiers.add(identity)
        if feature_key not in features:
            if f'msdata/raw/{candidate.filename}' not in INPUT_DIGESTS:
                raise ValueError(f'{pipeline}: unknown raw file {candidate.filename!r}')
            feature = features[feature_key] = BNode()
            graph.add((feature, DCTERMS.identifier, Literal(candidate.feature)))
            graph.add((feature, PROV.wasDerivedFrom, FILES[quote(candidate.filename, safe='')]))
        observation, result = BNode(), BNode()
        graph.add((observation, RDF.type, SOSA.Observation))
        graph.add((result, RDF.type, SOSA.Result))
        graph.add((observation, SOSA.hasFeatureOfInterest, features[feature_key]))
        graph.add((observation, SOSA.observedProperty, WIKIDATA.Q500256))
        procedure, software, (rank_field, score_field, adduct_field) = METHODS[candidate.method]
        graph.add((observation, SOSA.usedProcedure, procedure))
        graph.add((observation, PROV.used, software))
        graph.add((observation, SOSA.hasResult, result))
        graph.add((observation, DCTERMS.identifier, Literal(candidate.identifier)))
        add_number(graph, observation, rank_field, candidate.rank)
        add_number(graph, observation, score_field, candidate.score)
        if candidate.adduct:
            _add_property_value(graph, observation, SIO.SIO_000008, Literal(adduct_field), Literal(candidate.adduct))
        for subject, predicate, text in [
            (observation, DCTERMS.source, candidate.evidence),
            (result, DIRECT.P234, candidate.inchi),
            (result, DIRECT.P274, candidate.formula),
            (result, SDO.smiles, candidate.smiles),
            (result, RDFS.label, candidate.name),
        ]:
            if text:
                graph.add((subject, predicate, Literal(text)))
        add_key(graph, result, candidate.key)
        for identifier in candidate.pubchem:
            graph.add((result, DIRECT.P662, Literal(identifier)))
        for match in candidate.matches:
            if not re.fullmatch(r'Q[1-9][0-9]*', match.qid):
                raise ValueError(f'Invalid reported chemical QID {match.qid!r}')
            item = WIKIDATA[match.qid]
            if match not in references:
                reference = references[match] = BNode()
                graph.add((reference, RDFS.seeAlso, item))
                graph.add((reference, DCTERMS.source, Literal(match.origin)))
                if match.name:
                    graph.add((reference, RDFS.label, Literal(match.name)))
                add_key(graph, reference, match.key)
                if match.isomeric_smiles:
                    graph.add((reference, DIRECT.P2017, Literal(match.isomeric_smiles)))
                for identifier in match.pubchem:
                    graph.add((reference, DIRECT.P662, Literal(identifier)))
            graph.add((result, PROV.wasDerivedFrom, references[match]))
    return graph


def export_chemicals(pipeline, trial):
    reader = {'enpkg': read_enpkg, 'flock': read_flock}[pipeline]
    return chemical_graph(pipeline, reader(trial))


def inventory(graph):
    """Count hypotheses separately from the distinct structures those hypotheses describe."""
    full, connectivity, full_items, related_items = set(), set(), set(), set()
    observations = linked = 0
    for result in graph.objects(None, SOSA.hasResult):
        observations += 1
        key = graph.value(result, DIRECT.P235, any=False)
        if key is not None:
            full.add(str(key))
            connectivity.add(str(key)[:14])
        for identifier in graph.objects(result, SDO.identifier):
            if (identifier, SDO.propertyID, CONNECTIVITY_SCHEME) in graph:
                connectivity.update(map(str, graph.objects(identifier, SDO.value)))
        associated = False
        for reference in graph.objects(result, PROV.wasDerivedFrom):
            exact = key is not None and (reference, DIRECT.P235, key) in graph
            for item in graph.objects(reference, RDFS.seeAlso):
                (full_items if exact else related_items).add(item)
                associated = True
        linked += associated
    return observations, linked, {'full InChIKeys': full, 'connectivity blocks': connectivity, 'full-key Wikidata items': full_items, 'other Wikidata associations': related_items}

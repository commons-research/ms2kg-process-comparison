"""Export and compare the sample and acquisition profile without rerunning ETL."""

import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, PROV, SDO, SOSA

from benchmark_input import INPUT_DIGESTS, verify_input
from chemical_schema import export_chemicals, inventory
from flock.shared import read_samples as read_flock
from legacy_enpkg.shared import read_samples as read_enpkg
from record_store import snapshot
from shared_terms import DATA, FILES, WIKIDATA, write_turtle


ROOT = Path(__file__).resolve().parent
SAMPLES = Namespace(DATA + 'sample/')
ACQUISITIONS = Namespace(DATA + 'acquisition/')
SOURCE_MATERIALS = Namespace(DATA + 'source-material/')
IDENTIFICATIONS = Namespace(DATA + 'source-identification/')
SCAN_POLARITIES = Namespace(DATA + 'scan-polarity/')
DWC = Namespace('http://rs.tdwg.org/dwc/terms/')
DWCIRI = Namespace('http://rs.tdwg.org/dwc/iri/')
SIO = Namespace('http://semanticscience.org/resource/')
OBO = Namespace('http://purl.obolibrary.org/obo/')
POLARITY = {'pos': OBO.MS_1000130, 'neg': OBO.MS_1000129}
READERS = {'enpkg': read_enpkg, 'flock': read_flock}


def export_trial(pipeline, trial, metadata):
    """Write one graph from native evidence, using the verified source table only to check coverage."""
    with metadata.open(encoding='utf-8', newline='') as stream:
        expected = {row['sample_id']: row for row in csv.DictReader(stream, delimiter='\t')}
    graph = Graph()
    for prefix, namespace in (
        ('sample', SAMPLES), ('run', ACQUISITIONS), ('file', FILES),
        ('source', SOURCE_MATERIALS), ('identification', IDENTIFICATIONS), ('polarity', SCAN_POLARITIES),
        ('wd', WIKIDATA), ('obo', OBO), ('sio', SIO), ('dwc', DWC), ('dwciri', DWCIRI),
    ):
        graph.bind(prefix, namespace)
    for identifier, role, name, taxon, acquisitions in READERS[pipeline](trial):
        row = expected.pop(identifier, None)
        if row is None or (role, name) != (row['sample_type'], row['source_taxon']):
            raise ValueError(f'{pipeline}: unexpected or conflicting sample {identifier!r}')
        if sorted(acquisitions) != sorted((polarity, row[f'sample_filename_{polarity}']) for polarity in POLARITY):
            raise ValueError(f'{pipeline}: acquisition evidence differs from the input for {identifier}')
        sample_key = quote(identifier, safe='')
        sample = SAMPLES[sample_key]
        graph.add((sample, RDF.type, PROV.Entity))
        graph.add((sample, DCTERMS.identifier, Literal(identifier)))
        graph.add((sample, DCTERMS.type, Literal(role)))
        if role == 'sample':
            graph.add((sample, RDF.type, SOSA.Sample))
        if name:
            source_material = SOURCE_MATERIALS[sample_key]
            identification = IDENTIFICATIONS[sample_key]
            graph.add((sample, PROV.wasDerivedFrom, source_material))
            graph.add((identification, RDF.type, DWC.Identification))
            graph.add((identification, DCTERMS.subject, source_material))
            graph.add((identification, DWC.verbatimIdentification, Literal(name)))
            if taxon:
                graph.add((identification, DWCIRI.toTaxon, WIKIDATA[taxon]))
        for polarity, filename in acquisitions:
            key = quote(filename, safe='')
            acquisition = ACQUISITIONS[key]
            artifact = FILES[key]
            scan_polarity = SCAN_POLARITIES[key]
            graph.add((acquisition, RDF.type, PROV.Activity))
            graph.add((acquisition, RDF.type, OBO.OBI_0003097))
            graph.add((acquisition, PROV.used, sample))
            graph.add((acquisition, SIO.SIO_000008, scan_polarity))
            graph.add((scan_polarity, RDF.type, POLARITY[polarity]))
            graph.add((acquisition, DCTERMS.relation, artifact))
            graph.add((artifact, RDF.type, PROV.Entity))
            graph.add((artifact, RDF.type, SDO.MediaObject))
            graph.add((artifact, SDO.name, Literal(filename)))
            graph.add((artifact, SDO.sha256, Literal(INPUT_DIGESTS[f'msdata/raw/{filename}'])))
    if expected:
        raise ValueError(f'{pipeline}: missing sample records: {sorted(expected)}')
    write_turtle(graph, trial / 'shared-v2.ttl')
    return graph


def latest_workspace(build, pipeline):
    pointer = build / 'latest' / pipeline
    if not pointer.is_file():
        raise ValueError(f'No latest {pipeline} workspace. Pass {pipeline.upper()}=build/<workspace> to make shared.')
    return snapshot(build, pipeline, pointer.read_text(encoding='utf-8').removesuffix('\n')).parents[1]


def compare_workspaces(workspaces):
    reference = Graph().parse(ROOT / 'fixtures/toy-v2.ttl')
    graphs = []
    inventories = {}
    for pipeline, workspace in workspaces.items():
        source = workspace / 'input'
        verify_input(source)
        for label in ('first', 'second'):
            trial = workspace / label
            graph = export_trial(pipeline, trial, source / 'metadata/metadata.tsv')
            graphs.append(graph)
            missing, extra = reference - graph, graph - reference
            print(f'{trial / "shared-v2.ttl"}: {len(graph)} triples, {len(missing)} missing and {len(extra)} extra against the toy reference')
            for marker, difference in [('-', missing), ('+', extra)]:
                for triple in sorted(difference):
                    print(marker, *(term.n3() for term in triple))
            observations, linked, identifiers = inventory(export_chemicals(pipeline, trial))
            inventories[pipeline, label] = identifiers
            print(f'{trial / "chemicals-v2.ttl"}: {observations} candidate assertions, {linked} with a native Wikidata association')
    for label in ('first', 'second'):
        enpkg = inventories['enpkg', label]
        flock = inventories['flock', label]
        for category in enpkg:
            left, right = enpkg[category], flock[category]
            print(f'{label} {category}: {len(left & right)} shared, {len(left - right)} ENPKG only, {len(right - left)} Flock only')
    # The profile assigns IRIs to every resource and has no blank nodes.
    agree = all(set(graph) == set(graphs[0]) for graph in graphs[1:])
    print('All four sample/acquisition graphs agree.' if agree else 'Sample/acquisition graphs differ.')
    return agree and set(graphs[0]) == set(reference)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in READERS:
        parser.add_argument(f'--{name}', type=Path, help=f'completed {name} workspace (default: latest local record)')
    arguments = parser.parse_args()
    try:
        workspaces = {name: getattr(arguments, name) or latest_workspace(ROOT / 'build', name) for name in READERS}
        if not compare_workspaces(workspaces):
            sys.exit(1)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Shared export failed: {error}\n')

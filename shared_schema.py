"""Reconcile a trial's native sample, acquisition and chemical evidence."""

import argparse
import csv
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, PROV, SDO, SOSA

from benchmark_input import INPUT_DIGESTS
from chemical_schema import export_chemicals
from flock.shared import read_samples as read_flock
from legacy_enpkg.shared import read_samples as read_enpkg
from shared_terms import DATA, FILES, WIKIDATA, write_turtle


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
    """Build a graph from native evidence, using the verified source table to check coverage."""
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
    return graph


def reconcile(pipeline, trial, metadata):
    graph = export_trial(pipeline, trial, metadata)
    graph += export_chemicals(pipeline, trial)
    write_turtle(graph, trial / 'reconciled.ttl')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline', choices=READERS)
    parser.add_argument('trial', type=Path)
    parser.add_argument('metadata', type=Path)
    arguments = parser.parse_args()
    reconcile(arguments.pipeline, arguments.trial, arguments.metadata)

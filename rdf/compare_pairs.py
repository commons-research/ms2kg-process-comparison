"""Compare Wikidata taxon–chemical candidate pairs in a benchmark workspace."""

import argparse
import csv
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from rdflib import Graph, URIRef
from rdflib.namespace import PROV, SOSA
from rdflib.plugins.sparql import prepareQuery


DIRECTORY = Path(__file__).resolve().parent
PIPELINES = ('enpkg', 'flock')
STRUCTURE = URIRef('http://www.wikidata.org/entity/Q500256')
STRENGTHS = ('full-key', 'connectivity-only', 'unverified')


class Association(NamedTuple):
    taxon: str
    chemical: str
    software: str
    procedure: str
    strength: str

    @property
    def pair(self):
        return self.taxon, self.chemical


def read_graph(path, query):
    graph = Graph().parse(path, format='turtle')
    # Include reported methods even when none of their candidates has a linked Wikidata pair.
    methods = {(str(software), str(procedure))
               for observation in graph.subjects(SOSA.observedProperty, STRUCTURE)
               for software in graph.objects(observation, PROV.used)
               for procedure in graph.objects(observation, SOSA.usedProcedure)}
    return [Association(*map(str, row)) for row in graph.query(query)], methods


def method_link(iri):
    parts = urlsplit(iri)
    path = parts.path.rstrip('/').split('/')
    label = parts.fragment or (path[-2] if len(path) > 1 and path[-1] == 'README.md' else path[-1])
    return f'[{label or iri}](<{iri}>)'


def method_counts(pipeline, software, procedure, associations, other_pairs):
    pairs = {entry.pair for entry in associations}
    counts = [len(pairs), len(pairs & other_pairs), len(pairs - other_pairs)]
    counts.extend(len({entry.pair for entry in associations if entry.strength == strength}) for strength in STRENGTHS)
    return table_row(pipeline, method_link(software), method_link(procedure) if procedure else 'All procedures', *counts)


def table_row(*cells):
    return '| ' + ' | '.join(map(str, cells)) + ' |'


def compare(input_dir, output_dir):
    query = prepareQuery((DIRECTORY / 'taxon-chemical-pairs.rq').read_text(encoding='utf-8'))
    evidence_rows = []
    graphs = {pipeline: read_graph(input_dir / pipeline / 'reconciled.ttl', query) for pipeline in PIPELINES}
    pairs = {pipeline: {entry.pair for entry in associations} for pipeline, (associations, _) in graphs.items()}
    enpkg, flock = pairs['enpkg'], pairs['flock']
    method_rows = []
    for pipeline, other in [('enpkg', 'flock'), ('flock', 'enpkg')]:
        associations, methods = graphs[pipeline]
        for entry in associations:
            membership = 'both' if entry.pair in pairs[other] else f'{pipeline}-only'
            evidence_rows.append((*entry.pair, membership, pipeline, entry.software, entry.procedure, entry.strength))
        for software in sorted({software for software, _ in methods}):
            software_rows = [entry for entry in associations if entry.software == software]
            method_rows.append(method_counts(pipeline, software, None, software_rows, pairs[other]))
            for procedure in sorted(method for tool, method in methods if tool == software):
                procedure_rows = [entry for entry in software_rows if entry.procedure == procedure]
                method_rows.append(method_counts(pipeline, software, procedure, procedure_rows, pairs[other]))

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'pair-evidence.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(('taxon', 'chemical', 'membership', 'pipeline', 'software', 'procedure', 'strength'))
        writer.writerows(sorted(evidence_rows))
    summary = [
        '# Wikidata taxon–chemical candidate pairs', '',
        'Each pair links the identified source taxon of a biological sample to a candidate’s native Wikidata reference through that sample’s acquisition and raw file. A shared pair means both pipelines reported the same two Wikidata items. It does not establish compound presence, feature alignment or independent experimental confirmation.', '',
        '| ENPKG | Flock | Both | ENPKG only | Flock only | Union |', '|---:|---:|---:|---:|---:|---:|',
        table_row(len(enpkg), len(flock), len(enpkg & flock), len(enpkg - flock), len(flock - enpkg), len(enpkg | flock)),
        '', '## Pairs by annotation software and procedure', '',
        'For each row, “Also in other” counts distinct pairs found anywhere in the other pipeline. “Exclusive” counts pairs absent from that pipeline. Software totals take the union across procedures. A reported method with no qualifying pair has a count of zero.', '',
        '| Pipeline | Software | Procedure | Pairs | Also in other | Exclusive | Full key | Connectivity only | Unverified |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|', *method_rows, '',
        'The last three columns count distinct pairs with each kind of candidate-to-reference evidence. Full key requires identical complete InChIKeys. Connectivity only requires matching first blocks without a complete-key match. Unverified retains native associations with missing or disagreeing keys. One pair may have evidence in several columns or from several methods. See [pair-evidence.tsv](pair-evidence.tsv) for each distinct combination.', '',
    ]
    (output_dir / 'pair-summary.md').write_text('\n'.join(summary), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True, help='workspace containing enpkg/reconciled.ttl and flock/reconciled.ttl')
    parser.add_argument('--output-dir', type=Path, required=True, help='write pair-evidence.tsv and pair-summary.md here')
    arguments = parser.parse_args()
    compare(arguments.input_dir, arguments.output_dir)

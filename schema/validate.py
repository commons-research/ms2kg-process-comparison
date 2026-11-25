"""Validate each supplied Turtle graph against the common SHACL profile."""

import argparse
import gzip
from pathlib import Path

from pyshacl import validate
from rdflib import Graph


SCHEMA = Path(__file__).resolve().with_name('shapes-v2.ttl')


def validate_graph(data: Graph, shapes: Graph) -> None:
    conforms, _, report = validate(data, shacl_graph=shapes)
    if not conforms:
        raise ValueError(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graphs', type=Path, nargs='+', help='complete trial graphs in plain or gzip-compressed Turtle')
    arguments = parser.parse_args()
    shapes = Graph().parse(SCHEMA, format='turtle')
    failed = False
    for path in arguments.graphs:
        with (gzip.open(path, 'rb') if path.suffix == '.gz' else path.open('rb')) as source:
            data = Graph().parse(source, format='turtle', publicID=path.resolve().as_uri())
        try:
            validate_graph(data, shapes)
        except ValueError as violation:
            print(f'{path}: {len(data):,} triples, violations\n{violation}')
            failed = True
        else:
            print(f'{path}: {len(data):,} triples, conforms')
        del data
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())

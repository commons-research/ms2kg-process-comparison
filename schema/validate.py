"""Validate complete trial graphs separately against the common SHACL profile."""

import argparse
import gzip
from pathlib import Path

from pyshacl import validate
from rdflib import Graph


SCHEMA = Path(__file__).resolve().with_name('shapes-v2.ttl')
PUBLISHED = SCHEMA.parents[1] / 'rdf'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graphs', type=Path, nargs='*', help='Turtle files (plain or gzip). Defaults to the four published trials.')
    arguments = parser.parse_args()
    paths = arguments.graphs or [PUBLISHED / f'{pipeline}-{trial}.ttl.gz' for pipeline in ('enpkg', 'flock') for trial in ('first', 'second')]
    shapes = Graph().parse(SCHEMA, format='turtle')
    failed = False
    for path in paths:
        with (gzip.open(path, 'rb') if path.suffix == '.gz' else path.open('rb')) as source:
            data = Graph().parse(source, format='turtle', publicID=path.resolve().as_uri())
        conforms, _, report = validate(data, shacl_graph=shapes)
        print(f'{path}: {len(data):,} triples, {"conforms" if conforms else "violations"}', flush=True)
        if not conforms:
            print(report)
            failed = True
        del data
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())

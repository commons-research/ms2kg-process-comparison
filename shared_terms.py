"""Identifiers and Turtle publication shared by benchmark export profiles."""

import tempfile
from pathlib import Path

from rdflib import Namespace

PROJECT = 'https://github.com/commons-research/ms2kg-process-comparison'
DATA = PROJECT + '#10018590/'
FILES = Namespace(DATA + 'file/')
WIKIDATA = Namespace('http://www.wikidata.org/entity/')


def write_turtle(graph, destination):
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        graph.serialize(destination=temporary, format='turtle')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

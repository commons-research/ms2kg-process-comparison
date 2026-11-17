"""Validate the exported Turtle files and report their size and triple counts."""

import hashlib
import json
import sys
from pathlib import Path

from rdflib import Graph


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_graph.py OUTPUT_DIRECTORY", file=sys.stderr)
        return 2
    directory = Path(sys.argv[1])
    files = sorted(directory.glob("*_merged_graph.ttl"))
    if not files:
        print(f"No exported merged Turtle graphs in {directory}", file=sys.stderr)
        return 1
    report = []
    for path in files:
        graph = Graph()
        graph.parse(path, format="turtle")
        if len(graph) == 0:
            print(f"Empty RDF graph: {path}", file=sys.stderr)
            return 1
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        report.append({"file": path.name, "triples": len(graph), "sha256": digest.hexdigest()})
    print(json.dumps({"files": report, "total_triples": sum(item["triples"] for item in report)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

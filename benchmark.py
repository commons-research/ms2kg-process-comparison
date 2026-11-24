"""Record reproducible raw-to-RDF runs and compare results without running ETL."""

import argparse
import json
import math
import os
import re
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

import rdflib
from rdflib import BNode, Dataset, Graph, Literal, RDF, URIRef, XSD
from rdflib.compare import isomorphic

from benchmark_input import DATASET_SHA256, INPUT_DIGESTS, sha256, verify_input
from benchmark_plot import render_chart
from benchmark_publication import generation_name, store_comparison
from record_store import check_submission_directory, local_records, slug


ELAPSED = "Elapsed (wall clock) time (h:mm:ss or m:ss): "
RSS = "Maximum resident set size (kbytes): "
EXIT_STATUS = "Exit status: "
RDF_FORMATS = {".ttl": "turtle", ".nt": "nt", ".nq": "nquads"}
GRAPH_METRICS = (
    ("triples", "Distinct triples"), ("quads", "Graph statements"),
    ("subjects", "Distinct subjects"), ("objects", "Distinct objects"),
    ("predicates", "Distinct predicates"), ("classes", "Distinct IRI classes"),
    ("blank_nodes", "Blank nodes in triples"), ("named_graphs", "Named graphs"),
)


def read_gnu_time(path):
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        for prefix in (ELAPSED, RSS, EXIT_STATUS):
            if line.strip().startswith(prefix):
                if prefix in fields:
                    raise ValueError(f"{path} contains multiple GNU time measurements")
                fields[prefix] = line.strip().removeprefix(prefix)
    if not fields.keys() >= {ELAPSED, RSS, EXIT_STATUS}:
        raise ValueError(f"{path} is missing fields from GNU time -v")
    if fields[EXIT_STATUS] != "0":
        raise ValueError(f"{path} recorded exit status {fields[EXIT_STATUS]}")
    if not re.fullmatch(r"(?:\d+:)?\d+:\d+(?:\.\d+)?", fields[ELAPSED]) or not fields[RSS].isdigit():
        raise ValueError(f"{path} contains invalid GNU time measurements")
    wall_seconds = 0.0
    for part in fields[ELAPSED].split(":"):
        wall_seconds = wall_seconds * 60 + float(part)
    return {"wall_seconds": wall_seconds, "peak_rss_kib": int(fields[RSS])}


def load_rdf(paths):
    dataset = Dataset(default_union=True)
    normalize_literals = rdflib.NORMALIZE_LITERALS
    try:
        rdflib.NORMALIZE_LITERALS = False
        for path in paths:
            rdf_format = RDF_FORMATS.get(path.suffix.lower())
            if not rdf_format:
                raise ValueError(f"Unsupported RDF format in {path}. Use .ttl, .nt or .nq.")
            source = Dataset() if rdf_format == "nquads" else Graph(bind_namespaces="none")
            source.parse(path, format=rdf_format)
            if rdf_format == "nquads":
                statements = source.quads()
            else:
                statements = ((*triple, None) for triple in source)
            for subject, predicate, object_term, context in statements:
                if isinstance(object_term, Literal) and object_term.datatype == XSD.string:
                    object_term = Literal(str(object_term), normalize=False)
                if context is None or context == dataset.default_graph.identifier:
                    dataset.default_graph.add((subject, predicate, object_term))
                else:
                    dataset.add((subject, predicate, object_term, context))
    finally:
        rdflib.NORMALIZE_LITERALS = normalize_literals
    if not any(dataset.quads()):
        raise ValueError("RDF export contains no statements")
    return dataset


def encoded_quads(quads, default_identifier):
    graph = Graph(bind_namespaces="none")
    subject_role, predicate_role, object_role, graph_role = (
        URIRef(f"urn:benchmark:quad:{role}") for role in ("subject", "predicate", "object", "graph")
    )
    for subject, predicate, object_term, context in quads:
        statement = BNode()
        graph.add((statement, subject_role, subject))
        graph.add((statement, predicate_role, predicate))
        graph.add((statement, object_role, object_term))
        if context != default_identifier:
            graph.add((statement, graph_role, context))
    return graph


def same_rdf(first, second):
    first_quads, second_quads = set(first.quads()), set(second.quads())
    if first_quads == second_quads:
        return True
    if len(first_quads) != len(second_quads):
        return False
    if not any(isinstance(term, BNode) for quad in first_quads for term in quad):
        return False
    return isomorphic(
        encoded_quads(first_quads, first.default_graph.identifier),
        encoded_quads(second_quads, second.default_graph.identifier),
    )


def describe_rdf(dataset):
    subjects, objects, blank_nodes = set(), set(), set()
    predicates, classes, datatypes, languages, object_kinds = (Counter() for _ in range(5))
    triple_count = 0
    for subject, predicate, object_term in dataset.triples((None, None, None)):
        triple_count += 1
        subjects.add(subject)
        objects.add(object_term)
        predicates[str(predicate)] += 1
        if isinstance(subject, BNode):
            blank_nodes.add(subject)
        if isinstance(object_term, BNode):
            blank_nodes.add(object_term)
            object_kinds["blank_nodes"] += 1
        elif isinstance(object_term, Literal):
            object_kinds["literals"] += 1
            datatype = RDF.langString if object_term.language else object_term.datatype or XSD.string
            datatypes[str(datatype)] += 1
            if object_term.language:
                languages[object_term.language.lower()] += 1
        else:
            object_kinds["iris"] += 1
        if predicate == RDF.type and isinstance(object_term, URIRef):
            classes[str(object_term)] += 1
    default_graph = dataset.default_graph
    named_graph_sizes = [len(graph) for graph in dataset.graphs() if graph.identifier != default_graph.identifier]
    return {
        "triples": triple_count,
        "quads": len(default_graph) + sum(named_graph_sizes),
        "subjects": len(subjects), "predicates": len(predicates), "objects": len(objects),
        "classes": len(classes), "blank_nodes": len(blank_nodes),
        "named_graphs": len(named_graph_sizes), "default_graph_triples": len(default_graph),
        "object_kinds": object_kinds, "predicate_counts": predicates, "class_counts": classes,
        "literal_datatypes": datatypes, "literal_languages": languages,
    }


def file_info(path):
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}


def read_trial(timing, paths):
    return {
        "timing": read_gnu_time(timing),
        "timing_sha256": sha256(timing),
        "rdf": sorted((file_info(path) for path in paths), key=lambda entry: (entry["name"], entry["sha256"])),
    }


def write_report(args):
    check_submission_directory(args.submission)
    cohort = slug(args.cohort)
    pipeline = slug(args.pipeline) if args.pipeline is not None else None
    verify_input(args.input)
    if args.first_time.resolve() == args.second_time.resolve():
        raise ValueError("Provide separate timing files for the two trials")
    first_paths = [path.resolve() for path in args.first_rdf]
    second_paths = [path.resolve() for path in args.second_rdf]
    if set(first_paths) & set(second_paths):
        raise ValueError("Provide separate RDF output files for the two trials")
    trials = [read_trial(args.first_time, args.first_rdf), read_trial(args.second_time, args.second_rdf)]
    first, second = load_rdf(first_paths), load_rdf(second_paths)
    equivalent = same_rdf(first, second)
    trials[0]["graph"] = describe_rdf(first)
    trials[1]["graph"] = trials[0]["graph"] if equivalent else describe_rdf(second)
    report = args.submission / "benchmark.json"
    payload = {
        "schema": 3, "dataset_sha256": DATASET_SHA256, "input_sha256": INPUT_DIGESTS, "cohort": cohort,
        "trials": trials, "rdf_equivalent": equivalent,
    }
    if pipeline is not None:
        payload["pipeline"] = pipeline
    # Readers validate both the collection and each record directory while scanning them.
    with TemporaryDirectory(prefix=".benchmark-record-", dir=args.submission.resolve().parent.parent) as staging:
        staged = Path(staging) / report.name
        staged.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staged, report)
    print(report)


def nonnegative_integer(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def is_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)


def read_report(path):
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        schema = report["schema"]
        if type(schema) is not int or schema not in (2, 3):
            raise ValueError("expected a schema 2 or 3 raw-to-RDF submission")
        if report["dataset_sha256"] != DATASET_SHA256 or report["input_sha256"] != INPUT_DIGESTS:
            raise ValueError("submission does not identify the canonical raw input files")
        slug(report["cohort"])
        trials = report["trials"]
        if not isinstance(trials, list) or len(trials) != 2:
            raise ValueError("expected two trials")
        if schema == 2:
            # This format admitted only isomorphic datasets and stored their common metrics once.
            report["rdf_equivalent"] = True
        if type(report["rdf_equivalent"]) is not bool:
            raise ValueError("expected a boolean RDF equivalence result")
        for trial in trials:
            timing = trial["timing"]
            seconds = timing["wall_seconds"]
            if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
                raise ValueError("expected finite nonnegative wall time")
            if not nonnegative_integer(timing["peak_rss_kib"]) or not is_digest(trial["timing_sha256"]):
                raise ValueError("invalid peak memory or timing SHA-256")
            if not isinstance(trial["rdf"], list) or not trial["rdf"]:
                raise ValueError("expected RDF file evidence")
            for entry in trial["rdf"]:
                if not isinstance(entry["name"], str) or not nonnegative_integer(entry["bytes"]) or not is_digest(entry["sha256"]):
                    raise ValueError("invalid RDF file evidence")
            if schema == 2:
                trial["graph"] = report["graph"]
            graph = trial["graph"]
            if any(not nonnegative_integer(graph[key]) for key, _ in GRAPH_METRICS) or not 0 < graph["triples"] <= graph["quads"]:
                raise ValueError("invalid RDF counts")
        if report["rdf_equivalent"] and trials[0]["graph"] != trials[1]["graph"]:
            raise ValueError("equivalent datasets must have matching graph characteristics")
        return report
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{path}: {error}") from error


def equivalence_label(report):
    return "equivalent" if report["rdf_equivalent"] else "non-equivalent"


def check_profile(report, record):
    if "pipeline" not in report:
        raise ValueError(f"{record} needs a pipeline field naming a runnable profile")
    profile = Path("pipelines") / f"{slug(report['pipeline'])}.toml"
    if profile.parent.is_symlink() or profile.is_symlink() or not profile.is_file():
        raise ValueError(f"{record} needs a regular pipeline profile at {profile}")
    with profile.open("rb") as source:
        configuration = tomllib.load(source)
    for field in ("command", "rdf"):
        values = configuration.get(field)
        if not isinstance(values, list) or not values or not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError(f"{profile} needs a nonempty array of strings for {field}")


def chart_trials(reports):
    return {
        (f"{name} · run {number}", f"{source} · {equivalence_label(report)}"): trial
        for (source, name), report in reports.items()
        for number, trial in enumerate(report["trials"], start=1)
    }


def submissions_in(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Expected a submissions directory at {directory}")
    for path in sorted(directory.iterdir()):
        if path.name == "runbook-template.md" and path.is_file() and not path.is_symlink():
            continue
        yield path


def write_comparison(args):
    published = args.command == "publish"
    sources = [("Submitted", submissions_in(args.submissions))]
    if not published:
        if args.latest is not None:
            if args.latest.name != "latest":
                raise ValueError("--latest must name the latest directory in the local build")
            sources.append(("Local", local_records(args.latest.parent, legacy=args.local_submissions)))
        elif args.local_submissions is not None and (args.local_submissions.exists() or args.local_submissions.is_symlink()):
            sources.append(("Local", submissions_in(args.local_submissions)))

    reports = {}
    cohorts = defaultdict(dict)
    rows = []
    for source, directories in sources:
        for directory in directories:
            check_submission_directory(directory)
            record = directory / "benchmark.json"
            report = read_report(record)
            if published:
                check_profile(report, record)
            key = (source, directory.name)
            reports[key] = report
            cohorts[report["cohort"]][key] = report
            runbook_link = quote(os.path.relpath(directory / "README.md", args.output))
            record_link = quote(os.path.relpath(record, args.output))
            rows.append(f"| {directory.name} | {source} | {equivalence_label(report)} | [Runbook]({runbook_link}) · [Record]({record_link}) |")

    markdown = ["# ENPKG toy benchmark comparison", ""]
    charts = {}
    if reports:
        markdown += [
            "Each record contains two raw-to-RDF runs on the same canonical input. RDF equivalence compares the two outputs within a record.",
            "",
            "| Record | Source | RDF equivalence of runs 1 and 2 | Evidence |",
            "| --- | --- | --- | --- |", *rows, "",
            "## Raw-to-RDF timing", "",
            "Compare individual runs within the same declared machine and protocol cohort. Each panel has its own scale.", "",
        ]
        for cohort, members in sorted(cohorts.items()):
            plotted = chart_trials(members)
            metrics = [
                ("Wall time (s)", [trial["timing"]["wall_seconds"] for trial in plotted.values()], ",.2f"),
                ("Peak RSS (MiB)", [trial["timing"]["peak_rss_kib"] / 1024 for trial in plotted.values()], ",.1f"),
            ]
            charts[f"timing-{cohort}.svg"] = render_chart("Raw-to-RDF timing", plotted, metrics,
                                                          f"Cohort {cohort} | Individual runs from identical raw inputs")
        plotted = chart_trials(reports)
        graph_metrics = [(label, [trial["graph"][key] for trial in plotted.values()], ",d") for key, label in GRAPH_METRICS]
        charts["graph.svg"] = render_chart("RDF output characteristics", plotted, graph_metrics,
                                            "Different graph scopes. Counts do not establish equivalent coverage.")
    else:
        markdown.append("No benchmark submissions yet.")
    generation = generation_name(charts)
    if reports:
        for cohort in sorted(cohorts):
            markdown += [f"### {cohort}", "", f"![Wall time and peak memory for {cohort}]({generation}/timing-{cohort}.svg)", ""]
        markdown += ["## RDF output characteristics", "",
                     "The runbooks describe each pipeline's graph scope. Counts alone do not establish equivalent coverage.", "",
                     f"![RDF output characteristics by run]({generation}/graph.svg)"]
    store_comparison(args.output, generation, charts, "\n".join(markdown) + "\n", published=published, check=published and args.check)
    print(f"{len(reports)} submission(s) compared in {args.output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record", help="verify two local trials and record a submission")
    record.add_argument("--submission", type=Path, required=True)
    record.add_argument("--cohort", required=True)
    record.add_argument("--pipeline", help="runnable profile slug for a public submission")
    record.add_argument("--input", type=Path, required=True, help="canonical raw input directory used for both trials")
    for prefix in ("first", "second"):
        record.add_argument(f"--{prefix}-time", type=Path, required=True)
        record.add_argument(f"--{prefix}-rdf", type=Path, nargs="+", required=True)
    compare = commands.add_parser("compare", help="render the comparison from recorded submission data")
    compare.add_argument("--submissions", type=Path, default=Path("submissions"))
    compare.add_argument("--local-submissions", type=Path, help="include records from this optional local directory")
    compare.add_argument("--latest", type=Path, metavar="BUILD/latest", help="prefer completed local runs in this registry")
    compare.add_argument("--output", type=Path, default=Path("build"))
    publish = commands.add_parser("publish", help="render the public comparison using only eligible submitted records")
    publish.add_argument("--submissions", type=Path, default=Path("submissions"))
    publish.add_argument("--output", type=Path, default=Path("results"))
    publish.add_argument("--check", action="store_true", help="verify the complete publication without changing files")
    args = parser.parse_args()
    try:
        if args.command == "record":
            write_report(args)
        else:
            write_comparison(args)
    except (OSError, ValueError, SyntaxError, rdflib.exceptions.ParserError) as error:
        parser.exit(1, f"Benchmark failed: {error}\n")


if __name__ == "__main__":
    main()

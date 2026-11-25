# Contribute a schema or pipeline change

Fork the repository, clone the fork and create a branch from `main`. Keep changes to the [shared shapes](schema/shapes-v2.ttl), the [mapping guide](schema/README.md) and affected adapters in the same pull request. The external ENPKG and Flock implementations remain in their upstream repositories.

For a schema change, describe the scientific assertion being represented and the source that supports it. Add a conforming example and a violating example to `test_shacl.py`. Check both pipeline mappings. Update `fixtures/toy-v2.ttl` only when the expected sample or acquisition facts actually change. If a change breaks compatibility, version the shape and document how to interpret existing outputs. A measured run retains the shapes used to validate it.

For an adapter change, include a small native input and test the resulting RDF. Preserve the native annotation procedure, reference and uncertainty. Scores from different methods need their original meaning. A connectivity match alone must not be described as an exact structural identification.

Run `make check` for the offline tests. Use `make compare` for one fresh trial per pipeline on a provisioned machine. A pull request can describe the evidence and link an appropriately licensed external archive. Keep `runs/`, external installations, secret files and process logs private.

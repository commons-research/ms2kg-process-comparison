.DEFAULT_GOAL := help
python := .venv/bin/python
dependencies := .venv/.comparison-dependencies

.PHONY: help compare validate pairs check
help:
	@echo 'make compare                Run ENPKG and Flock once each on the same input'
	@echo 'make validate GRAPH=FILE    Validate a reconciled Turtle graph'
	@echo 'make pairs RUN=DIRECTORY    Recompute pair evidence from two reconciled graphs'

compare: $(dependencies)
	@$(python) -B pipeline.py

validate: $(dependencies)
	@test -n "$(GRAPH)" || { echo 'Supply GRAPH=/path/to/reconciled.ttl' >&2; exit 2; }
	@$(python) -B schema/validate.py "$(GRAPH)"

pairs: $(dependencies)
	@test -n "$(RUN)" || { echo 'Supply RUN=/path/to/comparison-run' >&2; exit 2; }
	@$(python) -B rdf/compare_pairs.py --input-dir "$(RUN)" --output-dir "$(RUN)"

check: $(dependencies)
	@$(python) -B -m unittest discover
	@$(python) -B -m unittest discover -s rdf

$(dependencies): requirements.txt
	@test -x $(python) || uv venv --python '>=3.11' .venv
	@uv pip install --python $(python) -r requirements.txt
	@touch $@

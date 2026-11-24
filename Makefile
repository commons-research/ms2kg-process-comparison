.DEFAULT_GOAL := help
profiles := $(basename $(notdir $(wildcard pipelines/*.toml)))
python := .venv/bin/python
dependencies := .venv/.benchmark-dependencies

.PHONY: help benchmarks results shared pairs validate
help:
	@echo "Read results/comparison.md for the submitted comparison"
	@echo "make pipeline <name>   Profiles: $(profiles)"
	@echo "make benchmarks        Preview submitted and local records in build/comparison.md"
	@echo "make shared            Check shared sample facts and compare chemical candidate inventories"
	@echo "make pairs             Compare taxon and chemical Wikidata pairs in the four published RDF graphs"
	@echo "make validate          Check the four published trial graphs against schema/shapes-v2.ttl"
	@echo "make results           Regenerate results/comparison.md from submissions only"

ifneq ($(filter pipeline,$(MAKECMDGOALS)),)
profile := $(filter $(profiles),$(word 2,$(MAKECMDGOALS)))
ifneq ($(MAKECMDGOALS),pipeline $(profile))
$(error Use make pipeline <name>. Profiles: $(profiles))
endif
ifeq ($(profile),)
$(error Select a pipeline. Profiles: $(profiles))
endif
.PHONY: pipeline $(profile)
pipeline: $(dependencies)
	@$(python) -B pipeline.py "$(profile)"
$(profile): pipeline
endif

benchmarks: $(dependencies)
	@$(python) -B benchmark.py compare --local-submissions build/records --latest build/latest
	@echo "Open build/comparison.md"

shared: $(dependencies)
	@$(python) -B shared_schema.py $(if $(ENPKG),--enpkg "$(ENPKG)") $(if $(FLOCK),--flock "$(FLOCK)")

pairs: $(dependencies)
	@$(python) -B rdf/compare_pairs.py --input-dir rdf --output-dir rdf

validate: $(dependencies)
	@$(python) -B schema/validate.py $(if $(GRAPH),"$(GRAPH)")

results: $(dependencies)
	@$(python) -B benchmark.py publish
	@echo "Open results/comparison.md"

$(dependencies): requirements.txt
	@python3 -m venv .venv
	@$(python) -m pip install --disable-pip-version-check -r requirements.txt
	@touch $@

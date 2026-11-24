.DEFAULT_GOAL := help
profiles := $(basename $(notdir $(wildcard pipelines/*.toml)))
python := .venv/bin/python
dependencies := .venv/.benchmark-dependencies

.PHONY: help benchmarks results
help:
	@echo "Read results/comparison.md for the submitted comparison"
	@echo "make pipeline <name>   Profiles: $(profiles)"
	@echo "make benchmarks        Preview submitted and local records in build/comparison.md"
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

results: $(dependencies)
	@$(python) -B benchmark.py publish
	@echo "Open results/comparison.md"

$(dependencies): requirements.txt
	@python3 -m venv .venv
	@$(python) -m pip install --disable-pip-version-check -r requirements.txt
	@touch $@

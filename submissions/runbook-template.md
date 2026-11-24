# Pipeline name and scope

Link `pipelines/<name>.toml`, the setup guide and the pinned mapping. Describe the entities, relationships, identifiers, named graphs and omissions someone needs to interpret the result.

## Source and environment

- External repository URL and full commit SHA for every required checkout
- Dependency lockfiles, runtime and tool versions, or image digests
- Public machine alias, cohort, CPU and available cores, RAM, OS and kernel, resource limits and GNU `time` version

## Canonical raw input and references

Give copyable setup commands from an empty directory. Show how the timed entry point reads the verified raw spectra and metadata, and document any sample or polarity filtering. Record auxiliary reference versions and checksums, required access, credential variable names without values, and live services.

## Run and validate

Give the `MS2KG_COHORT` and `make pipeline <name>` invocation, cache conditions and any installation-specific settings. List both trials' RDF outputs. Record the commands and observed results for any domain validation performed outside the timer.

## Evidence and reproduction limits

Link reviewed evidence with its version and SHA-256 when sharing is permitted. Give the paths to each timing report and RDF export. For unpublished or restricted evidence, explain what is unavailable and what a reader can verify independently. Disclose source modifications, redactions and service dependencies.

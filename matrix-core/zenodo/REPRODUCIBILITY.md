# Reproducibility record

## Environment and dependencies

Use CPython 3.12 and the exact pins in `../requirements.txt`. Dependency installation is the only networked setup step. Tests, examples, planner and benchmark run locally without network access. The benchmark manifest records Python/platform/CPU, package versions, schema and config hashes, commit, tracked working-tree hash, seeds, and command.

## Commands

From the repository root:

```sh
python -m pip install -r matrix-core/requirements.txt
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python -m unittest discover -s matrix-core/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/examples/end_to_end.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/scripts/sample_size_sensitivity.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/scripts/benchmark.py --seed 17 --held-out-seed 918273 --count 120 --output /tmp/matrix-core-final-benchmark.json
```

The fixed final held-out seed is public and the generator is known; it is not a blinded evaluation. Seeds 17 and 2026 were previously exposed during development. If the fixed held-out result influences code/configuration, disclose that and select a new seed and configuration before a subsequent evaluation.

## Artifact handling

Keep the raw JSON output unchanged alongside any derived summaries. Check `manifest.code_revision`, `working_tree_sha256`, `schema_sha256`, `config_sha256`, dependencies, and `run_command` before citing results. A dirty working tree is reported as dirty; do not cite such a run as a commit reproduction. Synthetic records are fictional and must never be replaced with participant or partner records. Do not upload this package or raw outputs to Zenodo without human governance approval.

## Result reporting

Report counts and denominators per policy and scenario class. Rates describe only this generated workload. No inferential intervals are calculated because cases are deterministic, stratified, and correlated; neither independence nor representativeness of a deployment/human population is justified. Include failures and explicitly mark commands or external reviews UNRUN.

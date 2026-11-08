# Matrix installation-core v0.1.0

**Status:** research prototype and executable reference policy. It is not a validated installation outcome, medical device, financial authorization, production service, compliance certification, or confirmation of a partner, funder, or grant.

The extension adds a disability-led, participant-governed installation contract to WorldHoloBridge. Participant stop and withdrawal are first-class controls; evidence, including negative findings, is retained as a research result rather than optimized away. Existing community governance and sponsor firewall remain authoritative.

## Contents

- [`schemas/v0.1.0/core.schema.json`](schemas/v0.1.0/core.schema.json): canonical language-neutral Draft 2020-12 contracts and reusable definitions. Each record and nested object is closed.
- [`matrix_core/`](matrix_core/): deterministic Python reference decisions, cross-record validation, and an in-memory finance reservation boundary.
- [`examples/`](examples/): wholly fictional JSON fixtures and an executable end-to-end example.
- [`tests/`](tests/), [`scripts/`](scripts/): schema/policy tests, seeded synthetic benchmark, and sensitivity-only sample-size planner.
- [`docs/`](docs/): protocol, threat/data boundaries, state machines, migration, accessibility, deployment blockers, and downstream integration guides.
- [`architecture/adr/`](architecture/adr/): design decisions.

## Reproduce locally

From the repository root, install the pinned Python dependencies once:

```sh
python -m pip install -r matrix-core/requirements.txt
```

After installation, test and evaluation commands make no network calls:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python -m unittest discover -s matrix-core/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/examples/end_to_end.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/scripts/benchmark.py \
  --seed 17 --held-out-seed 2026 --count 120 --output /tmp/matrix-core-benchmark.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/scripts/sample_size_sensitivity.py
```

The benchmark exports raw synthetic records/outcomes, run manifest, seeds, config and schema hashes, dependency versions, command, runtime metadata, denominators, per-class results, reason-code coverage and descriptive Wilson intervals. One warm-up call per implementation is excluded from latency. `--held-out-seed` is reported separately and must differ from the development seed; do not tune against it. Its scenarios are not independent human observations and cannot establish deployment safety. The oracle is separately implemented from the policy decision function but shares the contract specification.

## Record and decision rules

All records carry `schema_version`, `tenant_id`, `environment`, `classification`, `revision`, UUID `id`, and timezone-aware timestamps. The schema includes envelope and installation, participant, membership, access-preferences, consent, equipment, installation-check, participant-acceptance, organization, partner-engagement, referral, funding-case, budget-line, payment-intent, optional revenue-allocation, evidence, authorization, audit-event, and evaluation-run-manifest contracts. Cross-record validation enforces unique IDs, tenant-local references, active membership uniqueness, current-acceptance uniqueness and budget accounting. Accepted plan and equipment manifest references are version IDs, never mutable descriptions.

Policy decisions require a caller-injected aware clock. Activation checks tenant and trusted actor-role context, active participants, current scoped consent, current acceptance for exact plan/equipment versions, reviewed equipment, current required checks by an appropriate reviewer, and stop controls. Missing, stale, expired, unknown, or unreviewed inputs deny. Stop is immediate and does not consult finance; a stopped installation has no resume transition. Shared-installation withdrawal removes only that participant; withdrawal of the last participant stops the installation.

Referral consent is independent from signed engagement and publicity permission. Signed engagements require separate reviewed, unexpired agreement and signer-authority evidence; hashes alone do not establish authority. An organization proposal is not an affiliation or agreement. The included Neil Squire record is proposal-only, with no agreement evidence, signer authority, publicity permission, data-sharing scope, or enabled referral.

Evidence hashes support byte-integrity checks only; they do not prove truth, provenance, or signer authority. Execution status and independent review status are separate. Arena is optional education only and cannot affect support eligibility, consent, payment authority, or safety clearance.

## Finance boundary

Funding eligibility, approval, provider capability, and payment execution are separate. Payment intents are sandbox-only and contain integer minor units with an ISO currency code. The reference store checks approved funding, separate current approval/eligibility evidence, purpose, currency, tenant, available budget, exact canonical request digest, target revision, actor, expiry, one-time authorization consumption, and idempotency while holding one in-process lock. Only the same authorized finance actor can mark an unknown outcome, and a known outcome requires reviewed, unexpired reconciliation evidence bound to that intent. It has no provider adapter, bank credentials, or execution call. It is not durable, distributed, or production storage. A new key is not a retry strategy.

Financial records are closed and do not accept access narratives, diagnostic information, referral notes, or Arena telemetry; finance purposes and data scopes are constrained to enumerated values. Optional community revenue allocation is disabled unless separately reviewed policy-approval and funding-restriction evidence, a defined eligible revenue basis, and contractual compensation exist; participant benefits and wages are never a deduction basis.

## Downstream use

The schemas are canonical here and versioned. Consumers should pin `v0.1.0`, validate records locally, preserve strict-denial behavior, and avoid copying or modifying downstream repositories. See the integration guides for `spark-iis-api`, `levitate-disability-fx`, and `spark-ai-matrix-canada`.

## Deployment blockers

This prototype is not deployable until production identity/authentication and trusted actor context, durable transactional storage, provider agreements, verified current jurisdictional rules, independent security/privacy/accessibility review, and physical-device validation are completed. Human research additionally requires appropriate ethics, privacy, and accessibility review before recruitment. No human research or recruitment is authorized by these files.

## License and attribution

This is a repository extension and retains the root dual-license terms: code under MIT; documentation and templates under CC BY 4.0. See [`../LICENSE`](../LICENSE) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md). It does not alter existing country-node or research claims.

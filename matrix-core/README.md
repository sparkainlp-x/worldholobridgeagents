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
  --seed 17 --held-out-seed 918273 --count 120 --output /tmp/matrix-core-benchmark.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=matrix-core python matrix-core/scripts/sample_size_sensitivity.py
```

The benchmark exports raw synthetic records/outcomes, run manifest, seeds, config and schema hashes, dependency versions, command, runtime metadata, denominators, per-class results and reason-code coverage. It compares strict policy, a deliberately weak boolean gate, and three gate ablations (scoped consent, current acceptance, and required checks). Cases are deterministically generated and balanced by class; reported fractions describe only that workload. No inferential or population confidence intervals are calculated because cases are correlated by construction and are not sampled from a deployment or human population. The oracle is separately implemented from the policy decision function but shares the contract specification. Seeds 17 and 2026 appeared in earlier development outputs; 918273 is the fixed new held-out seed for final evaluation. The seed is not secret, the challenge specification is known, and any prior result exposure is recorded in the run manifest.

## Record and decision rules

All records carry `schema_version`, `tenant_id`, `environment`, `classification`, `revision`, UUID `id`, and timezone-aware timestamps. The schema includes envelope and installation, participant, membership, target-scoped actor-permission, access-preferences, installation-scoped consent, equipment, installation-check, participant-acceptance, organization, partner-engagement, referral, funding-case, budget-line, payment-intent, optional revenue-allocation, evidence, authorization, audit-event, and evaluation-run-manifest contracts. Cross-record validation enforces unique IDs, tenant/environment-local references, active membership uniqueness, current-acceptance uniqueness and budget accounting. Accepted plan and equipment manifest references are version IDs, never mutable descriptions.

Policy decisions require a caller-injected aware clock. Activation checks tenant and trusted actor-role context, active participants, current installation-scoped consent, current acceptance for exact plan/equipment/configuration versions, reviewed equipment, current accessibility and physical-safety checks from `matrix-installation-v0.1.0`, and stop controls. The required check list is enforced by code and cannot be waived by changing an installation record. Missing, stale, expired, unknown, conflicting, or unreviewed inputs deny. Stop records an immediate reference-state stop without asserting that physical equipment has stopped; no resume transition exists. Shared-installation withdrawal revokes only that participant's installation-scoped consents, memberships, acceptances, and referrals; withdrawal of the last participant stops the installation.

Referral consent is independent from signed engagement and publicity permission. Signed engagements require separate reviewed, unexpired agreement and signer-authority evidence; hashes alone do not establish authority. An organization proposal is not an affiliation or agreement. The included Neil Squire record is proposal-only, with no agreement evidence, signer authority, publicity permission, data-sharing scope, or enabled referral.

Evidence hashes support byte-integrity checks only; they do not prove truth, provenance, or signer authority. Execution status and independent review status are separate. Arena is optional education only and cannot affect support eligibility, consent, payment authority, or safety clearance.

## Finance boundary

Funding eligibility, approval, provider capability, and payment execution are separate. Payment intents are sandbox-only and contain integer minor units with an ISO currency code. The reference store checks a current target/action/tenant/environment-scoped fixture permission, approved funding, separate current approval/eligibility evidence, purpose, currency, available budget, exact canonical request digest, target revision, actor, expiry, one-time authorization consumption, and idempotency while holding one in-process lock. These caller-owned permission records do not authenticate their issuer. A known outcome requires reviewed, unexpired reconciliation evidence bound to that intent. There is no provider adapter, bank credentials, or execution call; storage is not durable, distributed, or production-ready. A new key is not a retry strategy.

Financial records are closed and do not accept access narratives, diagnostic information, referral notes, or Arena telemetry; finance purposes and data scopes are constrained to enumerated values. Optional community revenue allocation is disabled unless separately reviewed policy-approval and funding-restriction evidence, a defined eligible revenue basis, and contractual compensation exist; participant benefits and wages are never a deduction basis.

## Downstream use

The schemas are canonical here and versioned. Consumers should pin `v0.1.0`, validate records locally, preserve strict-denial behavior, and avoid copying or modifying downstream repositories. See the integration guides for `spark-iis-api`, `levitate-disability-fx`, and `spark-ai-matrix-canada`.

## Deployment blockers

This prototype is not deployable until production identity/authentication and trusted actor context, durable transactional storage, provider agreements, verified current jurisdictional rules, independent security/privacy/accessibility review, and physical-device validation are completed. Human research additionally requires appropriate ethics, privacy, and accessibility review before recruitment. No human research or recruitment is authorized by these files.

## License and attribution

This is a repository extension and retains the root dual-license terms: code under MIT; documentation and templates under CC BY 4.0. See [`../LICENSE`](../LICENSE) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md). It does not alter existing country-node or research claims.

The paper-source package under [`zenodo/`](zenodo/README.md) is not uploaded or registered. Its proposed CC BY 4.0 paper license does not change the repository's software or documentation licenses.

# Participant-governed installation-core reference architecture and synthetic evaluation protocol

**Status:** Working-paper source, not submitted. Protocol-style document only; not a registered preregistration. No human research or recruitment has occurred.

**License proposal:** CC BY 4.0 for a future paper deposit only, contingent on approval by all human authors. This statement does not change the repository's software or documentation license.

## Abstract

This working paper describes a language-neutral record contract and deterministic reference policy for a participant-governed installation workflow. Its scope includes scoped consent, participant acceptance, versioned checks, participant stop and withdrawal, bounded referrals, and sandbox-only finance reservation logic. It also specifies reproducible synthetic stress testing with a contract-derived oracle, deliberately weak baseline, and targeted gate ablations. The implementation is an unauthenticated, single-process research reference; no device controller, payment provider, partner transport, or human feasibility study is included. Synthetic workload behavior is not evidence of real-world installation safety, economic impact, banking readiness, compliance, or partner affiliation.

## 1. Motivation and prior work

The work is scoped to an existing community framework, not a replacement for its governance:

> Spark AI Matrix Country Prototype Framework. Zenodo record 23644437. https://zenodo.org/records/23644437

The record is cited as prior work only. This draft does not claim its authorship, endorsement, affiliation, or funding.

## 2. Architecture and governance boundary

The JSON Schema Draft 2020-12 contract is canonical and closed. The Python package provides deterministic policy decisions with injected time and explicit denial reason codes. Participant stop is independent of payment approval and records reference state only; it cannot guarantee physical shutdown. Withdrawal is scoped to one participant and installation and does not erase the accountability event. Arena is educational-only and absent from eligibility, consent, safety and payment decisions.

Finance remains distinct from grant eligibility, approval, provider capability, and execution. Requests are sandbox-only and bind a canonical digest to target revision, tenant, environment, actor, purpose, budget, integer minor-unit amount, and idempotency key. A lock-protected in-memory transaction demonstrates reservation semantics but is not distributed or durable production storage. No bank credentials or payment adapter exist.

## 3. Threat model and unresolved boundaries

The main assets are participant agency, scoped permissions, tenant/environment isolation, current configuration review, exact authorization, budget accounting, and evidence provenance. The reference checks trusted fixture permission records but cannot authenticate their source. It does not establish evidence truth, signer authority, hardware safety, legal eligibility, identity, or provider capability. Production authentication, durable transaction/audit, validated jurisdiction rules, physical-device testing, and independent privacy/security/accessibility review are deployment blockers.

Data remain in caller-owned objects/process memory; no human records should be supplied. Withdrawal revokes in-memory scoped records but retains audit/evidence. Any future service must define deletion, backups, audit minimization and lawful holds before collection. See the [threat and data-boundary model](../docs/threat-model-and-data-boundaries.md).

## 4. Synthetic evaluation protocol

The fixed generator uses class-balanced deterministic scenarios and separates development seed 17 from the new held-out seed 918273. Earlier seeds 17 and 2026 were already exposed in development output; 2026 is not represented as a fresh held-out set. The oracle validates the contract and directly checks intended policy conditions without calling the reference policy, but shares the same schema/specification assumptions.

Comparisons include a deliberately weak boolean baseline and ablations replacing current consent, current acceptance, or required checks with valid synthetic counterparts. Raw scenarios and decisions, per-class denominators, false allows/denials, valid-action completion, reason coverage, timing, environment, dependencies and hashes are exported. Because this is a deterministic stress workload rather than a probability sample, exact rates are descriptive workload fractions; no population uncertainty interval is calculated.

### Results

The fixed run used development seed 17 and held-out seed 918273, with 120 scenarios per seed (240 total). For the strict reference policy, false allows were 0/226 oracle-denied scenarios and false denials were 0/14 oracle-allowed scenarios; valid-action completion was 14/14. On the held-out split alone, these were 0/113 false allows, 0/7 false denials, and 7/7 valid-action completions. The deliberately weak boolean baseline had 161/226 false allows overall (81/113 held out), 0/14 false denials (0/7 held out), and 14/14 valid-action completions.

The consent, acceptance, and required-check ablations produced respectively 53/226, 38/226, and 42/226 false allows. The held-out false-allow counts were 27/113, 19/113, and 21/113. All ablations had 0/14 false denials. Eighteen generated scenario classes had 12–14 cases each; class-level denominators and outcomes are included in the raw export. Strict-policy median/p95 decision latency was 35,983,707/44,122,212 ns; baseline latency was 9,157.5/11,230 ns. Timings are specific to the recorded runtime and hardware.

This is a fixed, class-stratified deterministic workload, not an independent probability sample. Rates are descriptive only; no population confidence intervals or deployment-safety estimates are justified. The oracle independently computes expected labels from the contract but shares specification assumptions, so it is not an independent validator of the requirements. The held-out seed was not previously exposed or tuned against; the public generator and seed mean the run was not blinded. See [`results/final-synthetic-benchmark.json`](results/final-synthetic-benchmark.json) for raw cases, labels, decisions, per-class results, run command, hashes, dependency versions, and runtime metadata. The run used code revision `35e06e12698b5a8595691cb25426f0cbfbb580d7`; all 55 unit tests, the synthetic end-to-end example, and the assumption-only sample-size sensitivity script also completed successfully in that environment.

## 5. Future human feasibility protocol

Any human feasibility research is a separate future activity requiring appropriate ethics, privacy, accessibility and community governance review before recruitment. The single primary endpoint is independent completion of a prespecified installation task with participant-permitted accommodations. Secondary measures include time, errors, access barriers, burden, assistance, stops, withdrawal, missingness and adverse events. The manual installation checklist is the comparator when appropriate; allocation/order and learning effects must be prespecified. Income and job outcomes remain exploratory. No sample-size target, power claim, human outcome, or recruitment is asserted.

## 6. Reproducibility and status

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md), [`STATUS.md`](STATUS.md), and [`REQUIREMENTS-TO-EVIDENCE.md`](REQUIREMENTS-TO-EVIDENCE.md). No DOI is assigned. Metadata remains incomplete and must be completed by human authors. The paper's proposed CC BY 4.0 license is separate from the repository's existing code/documentation licenses. Human feasibility research, external scientific replication, production security review, identity authentication, durable storage, live integrations, and physical-device validation remain unrun or unresolved.

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

**UNRUN in this source draft.** Populate only from an actual execution of the documented final command and commit the unmodified raw export. Report all variant denominators and failures. Do not interpret synthetic false-allow rates as deployment-safety estimates.

## 5. Future human feasibility protocol

Any human feasibility research is a separate future activity requiring appropriate ethics, privacy, accessibility and community governance review before recruitment. The single primary endpoint is independent completion of a prespecified installation task with participant-permitted accommodations. Secondary measures include time, errors, access barriers, burden, assistance, stops, withdrawal, missingness and adverse events. The manual installation checklist is the comparator when appropriate; allocation/order and learning effects must be prespecified. Income and job outcomes remain exploratory. No sample-size target, power claim, human outcome, or recruitment is asserted.

## 6. Reproducibility and status

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md), [`STATUS.md`](STATUS.md), and [`REQUIREMENTS-TO-EVIDENCE.md`](REQUIREMENTS-TO-EVIDENCE.md). No DOI is assigned. Metadata remains incomplete and must be completed by human authors. The paper's proposed CC BY 4.0 license is separate from the repository's existing code/documentation licenses.

# Threat model and data-flow boundaries

## Assets and trust boundaries

Assets are participant agency, scoped consent, accepted plan/equipment versions, tenant isolation, safety/accessibility review, funding limits, authorization uniqueness, and integrity of evidence and evaluation records. The reference checks trusted fixture `actor_permission` records for exact actor, action, target, tenant, environment, role, expiry, and revocation. These records are only as trustworthy as their caller-controlled source: the prototype does not implement production authentication, identity proofing, permission-record signing, key management, tenant provisioning, provider identity, durable audit storage, or a physical-device controller.

The flow is: participant/authorized reviewer inputs → strict record validation → tenant-local reference checks → deterministic policy decision → audit event or sandbox budget reservation → synthetic evaluation export. Referral data is not sent by this package. Payment intents are not submitted. There are no external service calls or live credentials.

## Threats and controls

- Cross-tenant/environment record/reference or actor substitution: tenant/environment checks, explicit target-scoped fixture permissions, and actor-to-installation membership; production identity remains a blocker.
- Stale, revoked, overbroad or misdirected consent: explicit purpose, recipient, field scopes, validity, and revocation checked at decision time.
- Changed plans, equipment or configuration: acceptance and checks bind immutable version IDs/configuration.
- Unreviewed, expired or unknown evidence: deny privileged activation; digests establish integrity only.
- Sponsor or partner scope escalation: proposal, signed agreement evidence, separately reviewed/unexpired signer-authority evidence, publicity, and referral consent are distinct; no default referral.
- Stop suppression or automatic restart: a participant stop bypasses unrelated administrative-record validation, is audited and idempotent, and has no transition from stopped back to active. This records reference state only; it cannot switch off a physical device.
- Budget overspend, altered payload, replay, stale revision, or cross-tenant payment: exact digest/target/revision checks, one-time authorization, unique key, locked reservation.
- Uncertain payment result: reconciliation state blocks retry; no execution adapter exists.
- Arena score influencing support: Arena fields have no policy dependency.

## Retention, deletion, and export

The reference library keeps data only in caller-owned Python objects or process memory. It does not persist, transmit, log narrative content, or define production retention. A production adopter must specify participant-facing retention and deletion timelines, consent withdrawal propagation, deletion of derived copies/backups, audit minimization and lawful hold handling before collecting data. Audit records should retain only identifiers needed for accountability, not raw stories or diagnoses. Withdrawal revokes in-memory installation-scoped consents, memberships and referrals and removes the participant from further installation decisions, but does not erase the audit event or historical evidence; a real service must implement an approved retention/deletion schedule and lawful-hold procedure.

Benchmark output is reproducible synthetic data and includes raw generated records; store it only where appropriate for research artifacts. Do not put human records, partner correspondence, secrets, API keys, or credentials into examples or benchmark exports.

## Residual risk

Schema and reference logic cannot establish signer authority, truth of evidence, legal eligibility, safety of hardware, provider reliability, ethics, physical accessibility, or security of a deployment. Independent security/privacy/accessibility review and deployment blockers must be closed first.

## STRIDE-style review and unresolved priority

| Category | Example threat | Prototype control | Residual risk / required follow-up |
|---|---|---|---|
| Spoofing | Caller supplies another actor ID or role | Exact fixture permission and membership records | No identity proof or signed permission source; production authentication is a blocker |
| Tampering | Alter payment fields after authorization | Canonical digest binds target, revision, tenant, environment, actor, purpose, budget, amount, and idempotency key | Canonicalization/storage interoperability requires independent review |
| Repudiation | State transition lacks a record | Transition appends a unique audit event | In-memory only; no durable append-only log or external time authority |
| Information disclosure | Referral expands recipient or fields | Installation-scoped consent and organization recipient allowlist | No transport/data-access adapter exists to test; downstream enforcement remains unresolved |
| Denial of service | Malformed unrelated record blocks a stop | Stop validates only target and actor, preserves unrelated data, and records the stop | Physical shutdown path and availability engineering are unimplemented |
| Elevation of privilege | Empty caller check-list waives safety/accessibility | Versioned policy fixes required checks in the reference code | Policy governance and reviewer authenticity require independent oversight |

No likelihood or impact score is asserted: there is no deployment threat intelligence or measured exploitability evidence. Highest-priority blockers are production identity, durable transactional authorization/audit, physical-device validation, current jurisdiction review, and independent security/accessibility review.

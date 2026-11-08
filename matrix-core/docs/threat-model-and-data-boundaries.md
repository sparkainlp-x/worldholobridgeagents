# Threat model and data-flow boundaries

## Assets and trust boundaries

Assets are participant agency, scoped consent, accepted plan/equipment versions, tenant isolation, safety/accessibility review, funding limits, authorization uniqueness, and integrity of evidence and evaluation records. The prototype assumes caller-supplied actor identity is authentic; it does not implement authentication, key management, tenant provisioning, provider identity, durable audit storage, or a physical-device controller.

The flow is: participant/authorized reviewer inputs → strict record validation → tenant-local reference checks → deterministic policy decision → audit event or sandbox budget reservation → synthetic evaluation export. Referral data is not sent by this package. Payment intents are not submitted. There are no external service calls or live credentials.

## Threats and controls

- Cross-tenant record/reference or actor substitution: tenant checks and actor-to-membership role binding; production identity remains a blocker.
- Stale, revoked, overbroad or misdirected consent: explicit purpose, recipient, field scopes, validity, and revocation checked at decision time.
- Changed plans, equipment or configuration: acceptance and checks bind immutable version IDs/configuration.
- Unreviewed, expired or unknown evidence: deny privileged activation; digests establish integrity only.
- Sponsor or partner scope escalation: proposal, signed agreement evidence, separately reviewed/unexpired signer-authority evidence, publicity, and referral consent are distinct; no default referral.
- Stop suppression or automatic restart: participant can stop without finance; no transition from stopped back to active.
- Budget overspend, altered payload, replay, stale revision, or cross-tenant payment: exact digest/target/revision checks, one-time authorization, unique key, locked reservation.
- Uncertain payment result: reconciliation state blocks retry; no execution adapter exists.
- Arena score influencing support: Arena fields have no policy dependency.

## Retention, deletion, and export

The reference library keeps data only in caller-owned Python objects or process memory. It does not persist, transmit, log narrative content, or define production retention. A production adopter must specify participant-facing retention and deletion timelines, consent withdrawal propagation, deletion of derived copies/backups, audit minimization and lawful hold handling before collecting data. Audit records should retain only identifiers needed for accountability, not raw stories or diagnoses.

Benchmark output is reproducible synthetic data and includes raw generated records; store it only where appropriate for research artifacts. Do not put human records, partner correspondence, secrets, API keys, or credentials into examples or benchmark exports.

## Residual risk

Schema and reference logic cannot establish signer authority, truth of evidence, legal eligibility, safety of hardware, provider reliability, ethics, physical accessibility, or security of a deployment. Independent security/privacy/accessibility review and deployment blockers must be closed first.

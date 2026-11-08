# Data dictionary and boundaries

| Record | Purpose and minimum scope |
|---|---|
| Envelope | Version, UUID, tenant, environment, classification, revision, timezone-aware create/update timestamps |
| Installation | Status, opaque participant IDs, immutable accepted plan/equipment version IDs, fixed versioned accessibility/physical-safety check policy, configuration version, independent stop and optional Arena flags |
| Participant | Synthetic/pseudonymous label and status only; no legal name or contact details |
| Membership / actor permission | Installation role membership or exact actor/action/payment-target permission, tenant/environment, active state, expiry and revocation; fixture permissions do not authenticate an actor |
| Access preferences | Participant-selected accommodation codes and sharing scope; do not infer diagnoses |
| Consent | Installation and participant, explicit purpose, recipient, field scope, validity interval and revocation |
| Equipment / check | Manifest version and reviewed configuration; reviewer, review time and expiry; check type, status, reviewer and expiry |
| Participant acceptance | Exact plan, equipment-manifest and configuration versions accepted, time and withdrawal time |
| Organization / engagement / referral | Proposal or verified status with verification evidence, explicit engagement scope, separately reviewed/unexpired agreement and signer-authority evidence bound to the named signer, distinct publicity permission, and distinct referral recipient/purpose/field consent |
| Funding case / budget / payment | Separate approval and eligibility evidence, allowed purpose, integer currency minor units, reserved/settled budget, sandbox intent and reviewed reconciliation evidence bound to a settled intent |
| Revenue allocation | Optional and off by default; reviewed policy approval and funding-restriction evidence, eligible revenue basis, compensation; no participant wage/benefit deduction |
| Evidence | Provenance, review status, execution status and SHA-256 integrity digest; hash is not proof of truth or authority |
| Authorization | Exact request digest, target revision, tenant/environment/actor, expiry and consumption timestamp |
| Audit event | Subject, actor/role, action, decision, reason codes and occurrence time; no narrative payload |
| Evaluation run manifest | Seed, config/code/schema hashes, pinned dependencies, run command, runtime metadata and held-out flag |

## Role matrix

| Role | Reference capability |
|---|---|
| Participant | View own scoped information; stop installation immediately; withdraw only own acceptance from a shared installation |
| Facilitator | Request activation when all gates pass; coordinate installation; cannot override consent, acceptance, stop or missing checks |
| Accessibility lead | Review accessibility-related checks; cannot waive participant consent or stop |
| Safety reviewer | Review required safety checks; cannot waive participant consent or stop |
| Tenant administrator | Tenant-scoped operations; cannot cross tenants, waive consent, or resume a stopped installation |
| Finance approver | Approve exact sandbox reservation request; cannot execute a payment or access participant narrative |
| Partner | No access by default; a signed engagement and reviewed signer-authority evidence alone do not grant participant data. Referral needs separate exact participant consent |
| Sponsor | May fund infrastructure under governance firewall; no story control, participant-data access, or policy override |

Caller identity is not authenticated by this prototype. Finance examples require explicit target-scoped fixture permission records, but the caller-owned input store cannot prove who issued them; production authentication is a blocker. Do not place diagnoses, clinical or referral notes, access narratives, contact details, real bank or grant data, or Arena telemetry in finance payloads. Do not store direct identifiers or raw participant research data in the synthetic benchmark.

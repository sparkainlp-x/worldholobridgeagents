# State machines and record relationships

## Installation

Allowed reference transitions:

| From | To | Preconditions |
|---|---|---|
| `draft` / `ready` | `active` | `decide_activation` passes all current tenant, role, consent, acceptance, manifest, reviewer, check, evidence, and stop gates |
| `draft` / `ready` / `active` | `stopped` | Immediate participant, facilitator, tenant-admin, or safety-reviewer stop; no financial approval |
| `active` | `active` | A participant withdraws from a shared installation; only that participant's acceptance is withdrawn |
| Any non-terminal state | `withdrawn` | Reserved for future explicit governance workflow; not implemented |
| Any active or stopped state | `closed` | Reserved for future explicit governance workflow; not implemented |

`stopped`, `withdrawn`, and `closed` have no resume edge. The reference activation method rejects stale revisions, changed accepted plan/equipment versions, revoked or expired consent, stale checks, and any stop flag. A shared participant withdrawal removes that participant from the current participant list and records an audit event; withdrawal of the last participant transitions the installation to `stopped`.

## Payment intent

Allowed states are `draft`, `authorized`, `reserved`, `submitted`, `unknown`, `reconciliation_required`, `settled`, `cancelled`, and `failed`. The implemented reference transaction moves `draft`/`authorized` to `reserved` atomically with budget reservation and one-time authorization consumption. Only the same authorized finance actor can mark `reserved` as `reconciliation_required`. A known outcome may move `reserved` or `reconciliation_required` to `settled` only with reviewed, unexpired reconciliation evidence bound to that intent; cancellation/release and provider submission are not implemented. Unknown outcomes never trigger an implicit retry.

Every payment intent is sandbox-only. Authorization binds request digest, target ID and revision, tenant, sandbox environment, actor ID and role, expiry, and one-time consumption. Changed payloads, stale revisions, cross-tenant references, duplicate IDs, replay, budget overspend, and currency/purpose mismatches deny. One in-process lock is only a single-process reference transaction, not distributed idempotency.

## Relationships and uniqueness

UUID relationships are tenant-local. Installation participants, memberships, consents, acceptances, equipment, checks, evidence, organizations, partner engagements, referrals, funding cases, budgets, payments, authorizations, and audit subjects resolve to expected record types. IDs are unique in a record set. An active membership is unique per installation / participant / role; current acceptance is unique per installation / participant / immutable plan version / equipment manifest version. Budget reserved plus settled values cannot exceed a line's limit.

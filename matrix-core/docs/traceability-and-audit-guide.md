# Decision traceability and audit guide

## Reference transitions

The pure decision methods return `Decision(allowed, reason_codes)` and do not mutate records. Transition methods return a new record-list snapshot or a denial with the unchanged input snapshot. Each successful activation, stop, withdrawal, reservation, unknown payment outcome, or reconciliation appends a uniquely identified `audit_event`. The event contains identifiers, actor context, action, decision and reason codes—not participant narratives.

## Review sequence

1. Retain the exact versioned input snapshot and its tenant/environment boundary.
2. Record the called method, target ID, caller actor context and injected UTC clock value.
3. Validate each record against the versioned schema and cross-record rules. A denied `SCHEMA_INVALID:*`, `CROSS_TENANT_REFERENCE`, or `RELATIONSHIP_TARGET_MISSING` result should be addressed at the referenced record, not overridden.
4. Preserve every reason code returned by policy. Do not collapse a denial into a boolean or silently retry with broadened consent, a new idempotency key, or changed scope.
5. On a committed transition, retain the returned audit event with the transition snapshot. Verify that its `subject_id`, actor, event ID and time match the transition.
6. For a payment with unknown outcome, retain the reservation and unknown-state audit records; do not make a new request. Reconciliation must bind current reviewed evidence to the exact payment intent.

## Consent and withdrawal trace

An allowed referral must be traceable to a specific active installation, active participant membership, signed engagement, current agreement evidence whose authorized scope exactly matches the engagement, signer-authority evidence naming the engagement signer, organization-authorized recipient, and unrevoked consent for that installation, participant, purpose, recipient and field set. Publicity permission is separate.

Withdrawal revokes current consents, memberships, acceptances, and referrals for the withdrawing participant in that installation, then records an audit event. It does not erase historical audit/evidence, or revoke another installation's records. Production deletion/retention duties remain adopter responsibilities.

## Evaluation trace

Each raw benchmark row includes seed, held-out flag, case ID/class, original policy input, oracle label, each implementation decision/reason, timing, and source records. The run manifest binds the seed/configuration, schema hash, code revision, working-tree hash, dependency/runtime metadata and exact command. Rates are scenario-workload descriptions, not participant-level or deployment metrics.

## Integrity and limitations

SHA-256 is only a byte-integrity digest. It does not establish evidence truth, identity, reviewer authority, or event non-repudiation. The in-memory store is not a durable audit system. A deployment needs authenticated actor identities, immutable storage, access-controlled exports, retention/deletion controls, and independently reviewed audit procedures.

# Schema versioning and migration policy

`schemas/v0.1.0/core.schema.json` is the canonical versioned contract. Consumers must pin an exact version and record the schema hash with evaluation exports. Do not silently widen or reinterpret a released schema.

Breaking field, identifier, scope, enum, relationship, or state-machine changes require a new version and migration note. Compatible clarifications can be released as a patch only if validation and policy semantics remain unchanged. Preserve source revision and immutable plan/equipment version references for accepted records; never rewrite what a participant accepted.

Migrations must be deterministic, reviewable, preserve provenance and timestamps, record old/new schema versions and hashes, and fail closed for unmappable consent, authorization, or evidence status. Do not infer consent, approval, evidence truth, or partner status during migration. Keep historical records available only under an adopted retention/deletion policy.

Downstream integration should consume the canonical schema by pinned release/tag or immutable hash, validate at ingestion and before privileged decisions, and report unsupported versions as denied/unsupported rather than guessing.

# Integration guide: `spark-iis-api`

Treat this repository's `schemas/v0.1.0/core.schema.json` as the canonical contract. Pin the schema version/hash in the consuming service; validate envelopes and closed objects at the boundary, then apply tenant-local relationship and current-policy checks. Preserve denial codes and participant stop/withdrawal behavior.

Do not copy or modify the downstream repository as part of this extension. Do not interpret this reference package as authentication, durable storage, or a production API. Use only a synthetic/test environment until production identity, transactional storage, security review and privacy/accessibility approvals are in place.

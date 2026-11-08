# ADR 0002: No payment execution adapter

- **Status:** Accepted for research prototype v0.1.0
- **Decision:** Keep only sandbox payment intents and a lock-protected in-memory reservation/authorization/idempotency reference transaction. Do not add a provider client, credentials, or live execution.
- **Reason:** Grant eligibility, funding approval, provider capability, and execution are distinct decisions. A deterministic local boundary makes budget and replay behavior testable without initiating transfers.
- **Trade-off:** The reference store is neither durable nor distributed; it cannot safely coordinate multiple processes or resolve a real provider outcome.
- **Limit:** Unknown outcomes require reconciliation. Never retry under a new key until authoritative reconciliation. This ADR does not approve any real payment or financial product.

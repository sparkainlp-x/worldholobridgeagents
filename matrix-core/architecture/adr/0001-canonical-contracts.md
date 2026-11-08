# ADR 0001: Canonical, versioned record contracts

- **Status:** Accepted for research prototype v0.1.0
- **Decision:** One Draft 2020-12 schema is the canonical language-neutral contract; it contains reusable `$defs` and a `oneOf` over the closed record types. Downstream consumers pin this version rather than maintaining divergent copies.
- **Reason:** Explicit tenant, environment, classification, revision, timestamps, strict fields, and immutable accepted-version references are easier to audit and validate than implementation-specific payloads.
- **Trade-off:** Cross-record uniqueness, relationship and state-machine rules cannot be expressed as a single-record JSON Schema; the Python reference validator checks these separately.
- **Limit:** Schema validity does not establish evidence truth, consent quality, identity, authorization, accessibility, safety, or legal compliance.

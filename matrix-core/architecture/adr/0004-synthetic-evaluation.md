# ADR 0004: Synthetic policy evaluation

- **Status:** Adopted for research-prototype evaluation only.
- **Decision:** Generate deterministic, class-balanced synthetic cases using fixed development and held-out seeds. Compare the strict policy with a deliberately weak boolean-gate baseline and targeted ablations that remove the scoped-consent, current-acceptance, or required-check gate by replacing that input with a valid synthetic record. Use a separately written contract-derived oracle, export all inputs and outputs, and report exact scenario denominators and rates.
- **Rationale:** Negative cases should exercise explicit policy boundaries; raw rows and immutable run metadata support review and reproduction.
- **Limitations:** The oracle shares contract assumptions; scenarios are not sampled from deployments or people and are correlated by design. Exact synthetic workload rates have no population interpretation. The seed is public, not a cryptographic blind test.
- **Consequences:** No inferential confidence intervals or deployment-safety claims are reported. Do not tune on a held-out evaluation; record any seed/outcome exposure. Ablation outcomes diagnose implementation dependence on selected gates, not the causal value of a real-world intervention.

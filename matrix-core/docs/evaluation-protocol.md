# Synthetic policy stress-test protocol

## Status and scope

This is a reproducible software-policy protocol, not a human preregistration, registered study, or safety case. It does not recruit people or connect to live payment, referral, or device services.

## Fixed workload

The generator rotates through each named scenario class in a seeded permutation and balances class counts to within one case. Development and held-out seed values and the scenario configuration are included in each output. Seeds 17 and 2026 were visible in earlier development output; the current fixed final held-out seed is 918273. It is public rather than blinded. The test author knows the specification and deterministic scenario classes.

## Labels and comparisons

The oracle directly validates the closed contract and performs a separately implemented checklist of activation invariants; it does not call `decide_activation` or `validate_records`. It shares the schema and intended requirements, so it is implementation-independent but not specification-independent. Baselines are:

- **Weak boolean baseline:** checks only a present installation, a small set of booleans and caller role, intentionally omitting tenant, expiry, version, reviewer, and stop rigor.
- **No-consent ablation:** substitutes valid installation-scoped consent records.
- **No-current-acceptance ablation:** substitutes current plan/equipment/configuration acceptance.
- **No-required-check ablation:** substitutes passing checks for the fixed required checks.

All variants are judged against the original scenario's oracle label. Ablations are diagnostic counterfactual input substitutions, not alternative proposed policy designs.

## Metrics and uncertainty

Export oracle-allowed/denied denominators, false-allow and false-denial counts/rates, valid-action completion, reason-code coverage, per-class results, and median/p95 runtime. Exact rates describe only the generated workload. Cases are deterministic, class-balanced, and correlated within scenario classes; they are not a probability sample of people, devices, deployments, or partner decisions. No population confidence interval is appropriate or reported. Runtime results are hardware/runtime-specific.

## Reproducibility and stopping

Keep raw outcomes, seeds, configuration, commit/tree/schema hashes, dependencies, runtime metadata and command. Do not tune on the held-out outcomes. If any held-out result informs code or configuration changes, disclose exposure, choose and preregister a new seed/configuration before the next evaluation, and do not present the old set as held out. Report test failures and unrun commands; never replace missing output with assumed metrics.

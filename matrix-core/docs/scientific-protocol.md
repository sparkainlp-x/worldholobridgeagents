# Preregistration-style pilot protocol (future human feasibility research)

**Status:** Protocol template only. No human recruitment, data collection, or research is conducted by this repository. Do not recruit until independent ethics, privacy, and disability-led accessibility review, local approvals, and participant materials are approved.

## Scope and separation

1. **Software verification:** schema, state, invariants, boundary, concurrency, refusal and regression tests. This is not human evidence.
2. **Synthetic policy stress tests:** generated positive/negative fixtures, held-out seeds, independent contract-derived oracle and weak boolean-gate comparator. Results assess implementation behavior only; synthetic false-allow rates do not establish deployment safety.
3. **Future human feasibility research:** optional, separate study after the blockers above are closed. Results will be feasibility findings, not clinical or causal claims.

## Questions and endpoint

Questions: Can a participant complete a prespecified installation task using the prototype with accommodations chosen by that participant? What time, errors, access barriers, burden, assistance and adverse events arise? Does the software preserve stop, consent and withdrawal boundaries?

**Single primary human-feasibility endpoint:** proportion of enrolled participants independently completing the prespecified installation task using their permitted accommodations, within the prespecified task definition and review window. Define task success, permitted accommodations, missingness and denominator before enrollment. An accommodation is part of the task condition, not a failure.

Secondary outcomes: task time; count and severity of recoverable/unrecoverable errors; accessibility barriers and resolution; participant-reported burden; assistance requested/used; stop/withdrawal events; and adverse events. Income, employment, job placement, earnings and retention are exploratory only and cannot determine eligibility or be represented as causal effects.

## Comparator, order and assistance

If ethically and accessibly appropriate, compare with the existing manual installation checklist/workflow, not an inaccessible “no support” condition. Use randomized or counterbalanced order where feasible; predefine washout/practice effects, learning carryover and allocation sequence before recruitment. If order cannot be randomized, report the limitation and do not attribute differences to the software.

Permitted assistance is participant-chosen accommodation, interpreter, assistive technology, or a prespecified facilitator prompt available under both conditions. Record assistance category and timing, not unnecessary narrative. “Independent completion” means no task-solving intervention beyond the predeclared assistance/accommodations; it does not mean unaided or without assistive technology.

## Eligibility, exclusions and stopping

Recruit only after ethics and local approvals. Define inclusion/exclusion criteria in accessible language; exclude only for a safety/ethical reason or inability to give valid consent under an approved process, never based on disability category, low performance, use of accommodation, or Arena score. Document screening counts and reasons without identifying details.

Pause an individual task on participant request, distress, pain, fatigue, privacy concern, device/hardware hazard, repeated harmful output, or accessibility failure. Stop the study for a serious adverse event, consent or privacy breach, governance withdrawal, unresolved hardware risk, or repeated serious accessibility/safety failure. A participant stop is immediate and independent of financial approval. Provide an accessible withdrawal path and explain which already-collected data can/cannot be deleted under the approved protocol.

## Missingness and withdrawal

Report the number and reason category for missing endpoints, incomplete tasks, and withdrawals. Do not impute a withdrawn participant's endpoint as success. Primary denominator and any conservative missing-data sensitivity analysis must be preregistered. Preserve participant control over identifiable/raw data as approved; report aggregate results only when re-identification risk is acceptably low.

## Analysis and sample-size planning

Analysis unit is one participant's first prespecified task condition for the primary endpoint; repeated tasks are secondary and clustered within participant. Report numerator, denominator, proportion, uncertainty interval, missingness and adverse events. For comparator outcomes, report order/allocation and paired or clustered uncertainty where appropriate; do not assume repeated tasks are independent people.

No human sample size or power claim is asserted here. `scripts/sample_size_sensitivity.py` reports a planning-only normal-approximation grid for assumed proportions and precision. Assumptions are illustrative, not evidence. Reviewers must choose a justified estimand, precision, clustering/design effect and feasible recruitment plan before study; do not infer a target from the synthetic benchmark.

## Reporting commitment

Report negative findings, protocol deviations, accessibility failures, burden, stops, withdrawal, missing data and adverse events with denominators. Do not suppress failed or null results. Income/job outcomes remain exploratory. No claims of medical benefit, financial authorization, validated installation outcomes, confirmed funding, partner affiliation, or causal impact.

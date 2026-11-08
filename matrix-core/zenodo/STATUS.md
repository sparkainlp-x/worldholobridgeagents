# Evidence and claim status

| Area | Specified | Implemented | Executed | Independently reviewed | Unresolved |
|---|---|---|---|---|---|
| Closed record contracts and cross-record invariants | Yes | Yes | Unit tests and examples | Automated structural/code review only; not independent assurance | External consumer interoperability and schema release governance |
| Activation, scoped consent, stop and withdrawal | Yes | Yes, reference logic | Synthetic tests | Targeted read-only code review; no safety certification | Authenticated identities and physical-device behavior |
| Referral authorization | Yes | Yes, reference logic | Synthetic tests | Targeted review includes signer binding | Real agreements, verified jurisdictions, data transport/access enforcement |
| Sandbox finance store | Yes | Yes, in-memory only | Concurrency, replay and accounting tests | Code review only | Durable distributed transactions, production authentication, provider capability/execution |
| Synthetic benchmark | Yes | Yes | Fixed-seed 240-scenario run, 55 tests, example, and sensitivity planner executed; raw output in `results/final-synthetic-benchmark.json` | Oracle is separate code but shares specification; no independent scientific replication | Sampling representativeness and deployment safety are outside scope |
| Human feasibility protocol | Yes, as a future template | No human protocol registration | No recruitment or data collection | Not reviewed by an ethics board | Ethics/privacy/accessibility approvals and community governance |
| Working paper and Zenodo metadata | Draft specified | Local source and incomplete draft metadata; actual synthetic benchmark results documented | No upload; no human research | No external review | Human creators, rights, metadata completion, approval and any deposit |

**Status vocabulary:** specified = written requirement; implemented = code/docs exist; executed = command actually ran; independently reviewed = review with scope stated, not certification; unresolved = blocker or unperformed action. The phrase “preregistration-style” denotes a template only; it is not registered. No DOI, funding, affiliation, confirmed partner, validated outcome, or compliance certification is claimed.

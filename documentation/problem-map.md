# Problem-to-Solution Map

| Observed problem | Product response | Evidence |
| --- | --- | --- |
| No public examples | Generate independent tests, small oracles, and properties | Reproducible test cases and outcomes |
| Huge values or compressed inputs | Extract complexity limits before coding | Complexity claim checked against generated boundaries |
| Persistent state and temporal rules | Model transitions and invariants explicitly | State-machine and sequence tests |
| DAGs interpreted as unfolded trees | Separate node identity from path semantics | Shared-node and path-sensitive cases |
| Large geometric unions | Require compressed coordinate/event reasoning | Sparse large-coordinate cases |
| Ambiguous edge wording | Record interpretations and ask a critic to attack them | Competing interpretations and counterexamples |
| Model emits invalid source | Extract, parse, compile, inspect, and sandbox candidates | Static and dynamic verdicts |
| Candidate overfits its own tests | Separate test-design and implementation prompts | Evidence origin recorded per check |
| Deadline pressure | Enforce monotonic phase cutoffs and preserve the best candidate | Timing ledger and finalization reserve |
| Untrusted generated code | Execute in a resource-limited, networkless container | Sandbox status and resource measurements |

## Supplied Python acceptance themes

The six Python samples exercise congestion simulation with compressed events,
dynamic ordered collections, temporal reference resolution, recursively
flattened schemas, sparse worksheet geometry, and lexical capture over an
acyclic graph. They form an acceptance corpus, not a set of hardcoded targets.

---
name: Orchestration Change
about: Changes to the execution loop, workflow engine, or orchestration spine
title: '[ORCH] '
labels: 'core, needs-review, high-priority'
assignees: ''

---

## Objective
<!-- What orchestration behaviour is changing and why? -->

## Scope
<!-- Which orchestration components are touched? -->

**In scope:**
-

**Out of scope:**
-

## Affected Systems
- [ ] Execution loop
- [ ] Workflow engine
- [ ] Event bus / message routing
- [ ] Agent orchestration
- [ ] Backend / API
- [ ] Telemetry
- [ ] Persistence / State
- [ ] Other: ___

## Current Behaviour
<!-- Describe the current orchestration flow. -->

## Proposed Change
<!-- Describe the new orchestration flow. Include sequence diagrams or pseudo-code where helpful. -->

## Replay Impact
**Replay-safe:** Yes / No

<!-- MANDATORY: Describe how sequence_id and replay_hash are preserved or updated.
Any change to event ordering, envelope structure, or persistence contracts MUST be justified here. -->

## Determinism Validation
<!-- How will you verify that the new orchestration path remains deterministic?
List the test cases or replay scenarios that will be exercised. -->

- [ ]
- [ ]

## Migration Risk
<!-- Schema changes, state migration, or existing replay log compatibility. -->

## Risks
<!-- Concurrency, race conditions, duplicate orchestrators, hidden side-effects. -->

## Acceptance Criteria
- [ ]
- [ ]
- [ ]

## Telemetry Implications
<!-- New events or metric changes. All orchestration events must use canonical envelopes. -->

## Rollback Strategy
<!-- How do we revert this change if it destabilises production? -->

## References
<!-- Related issues, design docs, or prior discussions. -->

## Summary
<!-- One-paragraph description of what this PR does and why. -->

## Linked Issue
Closes #<!-- issue number -->

---

## Architectural Impact
<!-- Does this change affect the overall architecture? Describe any structural shifts. -->

## Determinism Validation
<!-- Does the change preserve deterministic execution? How was this verified? -->

- [ ] No nondeterministic ordering introduced
- [ ] No unstable event envelopes created
- [ ] sequence_id and replay_hash semantics unchanged (or explicitly documented)

## Replay Validation
<!-- Can the system replay events through this change without data loss or corruption? -->

- [ ] Replay-safe: existing replay logs remain valid after this change
- [ ] Tested with replay scenarios (describe below if applicable)

<!-- Replay test notes: -->

## Telemetry Impact
<!-- Are new events, metrics, or websocket payloads added or modified? -->

- [ ] No telemetry changes
- [ ] New canonical event envelopes added (documented in PR description)
- [ ] Existing envelope schema modified (backward-compatible)

## WebSocket Compatibility
- [ ] No websocket payload changes
- [ ] Websocket payload updated — backward-compatible
- [ ] Breaking websocket change — migration plan included

## Migration Risk
<!-- Are there schema changes, data migrations, or state-file changes? -->

- [ ] None
- [ ] Migration required (describe):

## Test Coverage
<!-- What tests cover this change? -->

- [ ] Unit tests added / updated
- [ ] Integration tests added / updated
- [ ] Replay scenario tested
- [ ] No tests required (justify):

## Rollback Strategy
<!-- How do we revert if this PR causes a regression in production? -->

## Screenshots
<!-- Required for any frontend changes. -->

## Notes for Reviewer
<!-- Anything the reviewer should pay special attention to. -->

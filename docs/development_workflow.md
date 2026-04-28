# Development Workflow — my_OS

This document provides the detailed Git flow, example commands, branch management procedures, squash strategy, and rollback procedures for contributing to **my_OS**.

For a high-level overview see [`CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## Table of Contents

1. [Ideal Development Flow](#ideal-development-flow)
2. [Branch Management](#branch-management)
3. [Commit Structure](#commit-structure)
4. [Squash Strategy](#squash-strategy)
5. [Merge Examples](#merge-examples)
6. [Rollback Strategy](#rollback-strategy)
7. [Release Stabilisation](#release-stabilisation)
8. [Hotfix Process](#hotfix-process)
9. [Replay Validation Checklist](#replay-validation-checklist)
10. [Telemetry Validation Checklist](#telemetry-validation-checklist)

---

## Ideal Development Flow

```
Issue (filed with correct template)
  │
  ▼
Branch created from develop
  │   git checkout develop && git pull origin develop
  │   git checkout -b feature/<short-description>
  ▼
Copilot / Agent Execution (scoped to one issue)
  │
  ▼
Local validation
  │   python -m pytest tests/ -q
  │   python -m compileall -q .
  ▼
PR opened → develop
  │   Title: [TYPE] Description (Closes #<issue>)
  │   Template fully filled out
  ▼
Code Review + CI Pass
  │
  ▼
Merge into develop (squash or merge commit)
  │
  ▼
Integration testing on develop
  │
  ▼
Release PR: develop → release/vX.Y.Z
  │
  ▼
Stabilisation on release branch
  │
  ▼
PR: release/vX.Y.Z → main
  │
  ▼
Tag vX.Y.Z on main
  │
  ▼
Merge release branch back into develop
```

---

## Branch Management

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/add-binance-ws-connector
```

### Creating a Research Branch

```bash
git checkout develop
git pull origin develop
git checkout -b research/llm-signal-scoring-spike
```

### Creating an Experiment Branch

```bash
git checkout develop
git pull origin develop
git checkout -b experiment/autonomous-rebalancer-prototype
```

### Keeping a Branch Up to Date

```bash
git fetch origin
git rebase origin/develop
# resolve any conflicts, then:
git rebase --continue
```

### Deleting a Merged Branch

```bash
# Locally
git branch -d feature/add-binance-ws-connector

# On remote
git push origin --delete feature/add-binance-ws-connector
```

---

## Commit Structure

All commits should follow the **Conventional Commits** pattern:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer: Closes #<issue>]
```

### Types

| Type | Use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `arch` | Architectural change |
| `refactor` | Code refactoring (no behaviour change) |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build, CI, or tooling changes |
| `perf` | Performance improvement |
| `revert` | Reverts a previous commit |

### Examples

```
feat(connectors): add Binance WebSocket order-book stream

Implements real-time L2 order-book ingestion via the Binance WS API.
Emits canonical OrderBookUpdateEvent envelopes on each tick.

Closes #42
```

```
fix(replay): correct replay_hash calculation for partial fills

The previous implementation excluded fill_quantity from the hash input,
causing divergence when replaying partial-fill sequences.

Closes #51
```

---

## Squash Strategy

| Scenario | Strategy | Rationale |
|---|---|---|
| `feature/*` → `develop` | **Squash merge** | Single clean commit per feature |
| `research/*` → `develop` | **Merge commit** | Preserve incremental research history |
| `experiment/*` (if ever merged) | **Squash merge** | Clean up experimental noise |
| `develop` → `release/*` | **Merge commit** | Full history must be traceable |
| `release/*` → `main` | **Merge commit** | Preserve release integrity |
| `hotfix/*` → `main` | **Merge commit** | Auditable production fix |

### Squash via GitHub UI

In the PR, select **"Squash and merge"** from the merge button dropdown.

### Squash via CLI

```bash
# While on develop, merge the feature branch with squash:
git merge --squash feature/add-binance-ws-connector
git commit -m "feat(connectors): add Binance WebSocket connector (closes #42)"
```

---

## Merge Examples

### Feature into develop

```bash
# Ensure develop is up to date
git checkout develop
git pull origin develop

# Merge (or squash via GitHub UI)
git merge --squash feature/add-binance-ws-connector
git commit -m "feat(connectors): add Binance WebSocket connector (closes #42)"
git push origin develop
```

### develop into release

```bash
git checkout -b release/v1.4.0
git push origin release/v1.4.0
# Open PR: release/v1.4.0 ← develop via GitHub UI
```

### release into main

```bash
# Via PR — must pass CI and have at least one approval
# After merge, tag:
git checkout main
git pull origin main
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin v1.4.0
```

### Merge release back into develop

```bash
git checkout develop
git pull origin develop
git merge release/v1.4.0
git push origin develop
```

---

## Rollback Strategy

### Revert a Merged Commit on develop

```bash
git checkout develop
git pull origin develop
git revert <commit-sha>
git push origin develop
# Open a PR if branch protection is active
```

### Revert a Merged PR on main (Production Rollback)

```bash
# Create a hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/revert-feature-xyz

# Revert the merge commit
git revert -m 1 <merge-commit-sha>

# Push and open a PR into main
git push origin hotfix/revert-feature-xyz
```

### Roll Back to a Previous Release Tag

```bash
git checkout main
git pull origin main
git checkout v1.3.2   # detached HEAD at known-good tag
# Deploy from this state
```

---

## Release Stabilisation

When `develop` reaches a milestone-complete state:

1. **Cut the release branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.4.0
   git push origin release/v1.4.0
   ```

2. **Run the full test suite**
   ```bash
   python -m pytest tests/ -q
   python -m compileall -q .
   ```

3. **Run replay validation** (see [Replay Validation Checklist](#replay-validation-checklist)).

4. **Run telemetry validation** (see [Telemetry Validation Checklist](#telemetry-validation-checklist)).

5. **Apply only critical fixes** — no new features on release branches.

6. **Open PR** `release/v1.4.0` → `main`.

7. **Merge and tag**.

8. **Merge release back into develop**.

---

## Hotfix Process

For urgent production repairs that cannot wait for the normal release cycle:

```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b hotfix/replay-hash-corruption

# 2. Apply minimal fix

# 3. Run tests
python -m pytest tests/ -q

# 4. Push and open TWO PRs:
#    hotfix/replay-hash-corruption → main
#    hotfix/replay-hash-corruption → develop
git push origin hotfix/replay-hash-corruption

# 5. After both PRs merge, tag main:
git checkout main && git pull origin main
git tag -a v1.3.3 -m "Hotfix: replay_hash corruption"
git push origin v1.3.3
```

---

## Replay Validation Checklist

Before merging into `main`, confirm all of the following:

- [ ] `sequence_id` values are unchanged for existing events
- [ ] `replay_hash` calculation is unchanged (or explicitly migrated)
- [ ] Event envelope schema is backward-compatible
- [ ] Replay restoration test passes with a known-good event log snapshot
- [ ] No new nondeterministic ordering introduced
- [ ] Persistence writes are idempotent under replay

---

## Telemetry Validation Checklist

Before merging into `main`, confirm all of the following:

- [ ] All new events use canonical envelopes
- [ ] No existing websocket payload contracts broken
- [ ] New metrics/events documented in PR description
- [ ] Telemetry does not introduce side-effects on replay
- [ ] Event emission is observable and interruptible

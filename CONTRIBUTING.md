# Contributing to my_OS

Thank you for contributing to **my_OS** — a deterministic, replay-safe, AI-native operational OS.

This guide covers the branch strategy, PR lifecycle, issue lifecycle, Copilot workflow, merge policy, release policy, and engineering rules required to keep the codebase stable and production-ready.

---

## Table of Contents

1. [Branch Strategy](#branch-strategy)
2. [Issue Lifecycle](#issue-lifecycle)
3. [PR Lifecycle](#pr-lifecycle)
4. [Copilot / Agent Workflow](#copilot--agent-workflow)
5. [Merge Policy](#merge-policy)
6. [Release Policy](#release-policy)
7. [Replay-Safety Engineering Rules](#replay-safety-engineering-rules)
8. [Label Strategy](#label-strategy)
9. [Branch Protection Recommendations](#branch-protection-recommendations)

---

## Branch Strategy

| Branch | Purpose | Stability |
|---|---|---|
| `main` | Production-only. Always deployable. | 🔒 Protected |
| `develop` | Integration branch. Receives completed feature PRs. | 🔒 Protected |
| `feature/*` | One coherent feature per branch. | Unstable until merged |
| `research/*` | Research, signal engines, roadmap experiments. | Unstable |
| `experiment/*` | Speculative / frontier AI work. Safe sandbox. | Highly unstable |
| `hotfix/*` | Urgent production repairs. Merges into `main` and `develop`. | Fast-track |
| `release/*` | Stabilisation before promoting to `main`. | Freeze |

### Naming Examples

```
feature/signal-engine-v2
feature/connector-binance-ws
research/hyperparameter-meta-learning
experiment/llm-orchestration-prototype
hotfix/replay-hash-corruption
release/v1.4.0
```

---

## Issue Lifecycle

1. **Open an issue** using the correct template (see `.github/ISSUE_TEMPLATE/`).
2. Apply relevant **labels** (see [Label Strategy](#label-strategy)).
3. Assign the issue to a milestone or sprint if applicable.
4. Link the issue to a branch when work begins.
5. Close the issue by merging the PR that resolves it (`Closes #<issue>`).

### Issue Templates

| Template | Use Case |
|---|---|
| `feature_request.md` | New capability or enhancement |
| `bug_report.md` | Defect or unexpected behaviour |
| `architecture_task.md` | Structural / design engineering |
| `research_spike.md` | Time-boxed investigation or experiment |
| `orchestration_change.md` | Changes to the execution loop or workflow engine |

---

## PR Lifecycle

```
Issue → Branch → Implementation → Tests → PR → Review → Merge into develop
                                                              ↓
                                                    Integration testing
                                                              ↓
                                                    Release PR into main
```

### PR Rules

- One PR per issue / capability. **No multi-system PRs.**
- Target branch is **`develop`** (never push directly to `main`).
- Fill out the PR template completely (`.github/pull_request_template.md`).
- Link the PR to the issue with `Closes #<issue>`.
- At minimum one approval is required before merging.
- CI must pass before merge.

### PR Naming

```
[TYPE] Short description of the change

Examples:
[FEATURE] Add Binance WebSocket connector
[FIX] Correct replay_hash calculation for partial fills
[ARCH] Refactor orchestration loop to single-spine pattern
[RESEARCH] Prototype LLM-assisted signal scoring
[HOTFIX] Emergency patch for sequence_id collision
```

---

## Copilot / Agent Workflow

GitHub Copilot coding-agent sessions must follow these rules:

### Mandatory Rules

1. **One issue per branch** — Each Copilot session targets exactly one open issue.
2. **One capability per PR** — Do not bundle unrelated changes.
3. **Avoid multi-system PRs** — Keep bounded contexts isolated.
4. **Preserve deterministic runtime** — Never introduce nondeterministic ordering.
5. **Preserve canonical event envelopes** — Do not invent new event schemas.
6. **No duplicate orchestrators** — Integrate into the existing orchestration spine.

### Best Practices

- **Architecture-first prompting** — Describe the structural goal before the implementation detail.
- **Scoped prompts** — One capability per prompt session; reset context between issues.
- **Replay-safe changes** — Always ask: "Does this change affect sequence_id or replay_hash?"
- **Conflict minimisation** — Fetch and rebase from `develop` before opening a PR.
- **Merge-safe patch stacking** — Keep commits small and independently revertable.

### Example Copilot Session Flow

```bash
# 1. Create branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-new-capability

# 2. Implement changes scoped to the issue

# 3. Run tests
python -m pytest tests/ -q

# 4. Commit with descriptive message
git add .
git commit -m "feat: add my-new-capability (closes #42)"

# 5. Open PR targeting develop
```

---

## Merge Policy

| Target | Strategy | Notes |
|---|---|---|
| `feature/*` → `develop` | Squash or merge commit | Squash preferred for clean history |
| `research/*` → `develop` | Merge commit | Preserve research context |
| `develop` → `release/*` | Merge commit | No squash — preserve full history |
| `release/*` → `main` | Merge commit | Tags applied here |
| `hotfix/*` → `main` | Merge commit | Also merge back into `develop` |

**Force push is never permitted on `main` or `develop`.**

---

## Release Policy

```
develop → release/vX.Y.Z → main
```

1. Cut a `release/vX.Y.Z` branch from `develop` when the milestone is complete.
2. Run stabilisation: full test suite, replay validation, telemetry validation.
3. Fix only critical regressions on the release branch.
4. Open a PR from `release/vX.Y.Z` → `main`.
5. After merge, tag `main` with `vX.Y.Z`.
6. Merge `release/vX.Y.Z` back into `develop` to capture any stabilisation fixes.

### Hotfix Policy

```
main → hotfix/description → main + develop
```

1. Branch `hotfix/<description>` from `main`.
2. Apply the minimal fix.
3. Open PRs into both `main` and `develop`.
4. Tag `main` with the patch version after merge.

---

## Replay-Safety Engineering Rules

These rules are **non-negotiable** and apply to every contribution.

1. **Preserve `sequence_id` semantics** — Never reorder, renumber, or deduplicate by `sequence_id` alone.
2. **Preserve `replay_hash`** — Do not mutate the hash calculation without a documented migration.
3. **Idempotent persistence** — All writes should be safe to replay. Prefer `(sequence_id, replay_hash, event_type)` composite keys.
4. **No nondeterministic ordering** — Do not rely on dict insertion order, set iteration, or unsorted queries for event sequencing.
5. **No hidden side-effects** — All state mutations must emit a canonical telemetry event.
6. **No parallel orchestrators** — There is one orchestration spine. New execution paths must integrate with it.
7. **Observable agents** — All agents must emit telemetry, remain interruptible, and be replay-compatible.

---

## Label Strategy

| Label | Meaning |
|---|---|
| `core` | Core runtime or orchestration |
| `runtime` | Execution loop changes |
| `research` | Research / spike work |
| `frontend` | UI changes |
| `backend` | Backend / API changes |
| `api` | Public API surface changes |
| `agents` | Agent framework changes |
| `connectors` | External data / exchange connectors |
| `telemetry` | Metrics, events, observability |
| `infra` | CI/CD, Docker, deployment |
| `security` | Security-sensitive changes |
| `performance` | Performance optimisation |
| `experimental` | Speculative / unstable work |
| `breaking-change` | Breaks backward compatibility |
| `high-priority` | Must be addressed urgently |
| `replay-safe` | Confirmed replay-safe |
| `needs-review` | Awaiting reviewer assignment |
| `blocked` | Blocked by another issue or PR |

---

## Branch Protection Recommendations

Apply these settings via **GitHub → Settings → Branches**.

### `main`

- ✅ Require a pull request before merging
- ✅ Require at least 1 approval
- ✅ Require status checks to pass (CI workflow)
- ✅ Require branches to be up to date before merging
- ✅ Block force pushes
- ✅ Block direct commits (include administrators)

### `develop`

- ✅ Require a pull request before merging
- ✅ Require at least 1 approval
- ✅ Require status checks to pass (CI workflow)
- ✅ Block force pushes

---

For the detailed Git flow walkthrough with example commands, see [`docs/development_workflow.md`](docs/development_workflow.md).

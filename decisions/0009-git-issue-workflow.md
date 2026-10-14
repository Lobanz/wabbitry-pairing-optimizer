# ADR 0009 — Git / issue workflow: each phase is an issue + branch + PR

Status: **Accepted** (2026-10-15); amended 2026-10-15 (commit-before-impl; PRs after)

## Context

The operator values audit trails ("audit logs keep people honest") and per-change
attribution. The implementation is phased, and each phase is a reassessment gate.

## Decision

- **Each phase** = its own **issue + branch + PR**:
  - a GitHub **issue** documenting the phase's goal, deliverables, and
    reassessment gate;
  - a dedicated **branch** (`phase/<n>-<slug>`) per phase;
  - a **PR** referencing the issue on completion, merged after the reassessment
    gate and operator review.
- **Design changes / feature additions / direction changes** each get their own
  **issue** documenting them — nothing is done silently. An issue is the audit
  record for every decision and change.
- **Harvest decisions into `decisions/` ADRs** so the audit trail is complete
  (this ADR is part of that harvest).
- **Amendment (2026-10-15):** direct commits to `main` are fine for the design
  foundation before impl; **PRs begin once the implementation phases start**
  ("after impl we'll do PRs"). Phase branches carry each phase's work.

## Motivation

- Keeps a per-change attribution trail matching the operator's audit value.
- Makes each phase's learning a reviewable unit (issue → branch → PR).
- The commit-before-PR amendment keeps the foundational design work moving
  without forcing premature PR review.

## Consequences

- Repo `Lobanz/wabbitry-pairing-optimizer` has a `phase-<n>` label set.
- Phase issues use the body template (goal / acceptance criteria / decisions /
  facts / out-of-scope) from the github-issues skill.
- PRs reference `Fixes #N` only when acceptance criteria are fully met;
  otherwise `Refs #N`.

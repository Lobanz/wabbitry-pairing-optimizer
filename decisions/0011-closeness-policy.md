# ADR 0011 — Closeness policy: keep it simple (minimize r)

Status: **Accepted** (2026-10-15)

## Context

Line-breeding locks in desirable traits, so one might expect the optimizer to
seek close pairings sometimes. But a full-solution score that *minimizes* total r
pushes toward outcrossing everything, which could conflict with deliberate
line-breeding.

## Decision

**Keep it simple for now: minimize total r.** More outcross is better as the
shipped default. Deliberate line-breeding to lock in traits happens via the
**operator's fixed-pairs** (e.g. Yaz × the Betsy-line), not something the
optimizer seeks on its own.

The closeness objective and its weight are **functionalized / seams** (isolated,
config-weighted components in the scoring), so a later "target closeness band" or
"line-breeding preference" can be added without touching the solver. But the
shipped default is straightforward outcross-minimization.

## Motivation

- The operator chose the simple default at this stage; it's the least-surprising
  behavior and the easiest to reason about and validate first.
- Fixed-pairs already encode the deliberate line-breeding (e.g. Yaz), so the
  optimizer doesn't need to discover it.

## Consequences

- `sum-r` has positive weight (minimize inbreeding) in the full-solution score.
- Line-breeding enters via fixed-pairs, not optimizer exploration.
- The seam keeps the door open to a closeness-preference knob later, with no
  solver rewrite (see ADR 0008).

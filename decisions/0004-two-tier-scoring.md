# ADR 0004 — Two-tier scoring: per-pairing + full-solution

Status: **Accepted** (2026-10-15)

## Context

A breeding round produces many candidate pairings. We need to rank (a) which
buck to pick *for one doe* and (b) which *complete assignment set* is best.
These are different decisions, so they use different scorers.

## Decision

Two separate scoring tiers:

**Tier 1 — per-pairing** (picks the best buck for one doe): weighted `r` +
weighted doe-production-history (doe productivity index). Breaks equal-r ties
by preferring the doe with the better production record.

**Tier 2 — full-solution** (ranks complete assignment sets from multi-start):
a weighted sum of six components —
1. sum of r (minimize inbreeding),
2. sum of doe-production-history,
3. unbred-doe penalty (order-trap artifact — a doe left with no compatible buck;
   NOT a sparse own-record like maxine n=1),
4. sibling last-resort penalty (forced full-sib pairing),
5. schedule length (operator labor; negative weight),
6. pairability (mixed-pair availability count).

All weights are **operator-policy**, held in the TOML config (`[scoring.*]`), and
**carried in the output** for auditability — the score is an opinion, not a fact,
and the report states it.

## Motivation

- Tier 1 answers the local assignment question; Tier 2 answers the global
  "which round plan is best" question. Conflating them loses information.
- The unbred-doe penalty (#3) is specifically an **order-trap discriminator**:
  without it, all solutions that leave the same doe unbred tie, hiding which
  ordering caused it.
- Emergent properties (schedule, pairability) only exist at the full-solution
  level, so they belong in Tier 2, not Tier 1.

## Consequences

- Only the **winning solution's** artifacts (its solution scores and pairing
  scores) are emitted — not top-N, no ledger.
- Weights are tunable in config with no code change (see ADR 0007).
- The scoring artifacts are a stated operator policy, auditable in the report.

## Amendment (2026-10-15, operator ruling at the Phase 3 gate)

The tier label is **relationship-aware**, not r-only. Probing the real roster
showed r≥0.5 conflates three very different cases:
- **parent-offspring** (e.g. zeek × abby, r=0.5) = NORMAL, allowed line-breeding
  (design §3 rule 8) -> tier `line_bred` (penalty 1).
- **founder-sister** (abigail × betsy, ginseng × harmony, r=0.5 via S) =
  legitimate founder diversity -> tier `line_bred` (penalty 1).
- **true same-generation full-sib** (same sire+dam: abby × amber, betty × lily)
  = last-resort -> tier `sibling` (penalty 5).

Only true full-sibs carry the heavy sibling penalty; parent-offspring and
founder-sisters do not. Enforced via `relationship_kind()` + `tier_for_pair()`
in kinship.py. Penalty values remain operator-policy in config.

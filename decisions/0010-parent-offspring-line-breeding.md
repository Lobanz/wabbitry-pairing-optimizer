# ADR 0010 — Parent-offspring is normal line-breeding; "feasible" is permissive

Status: **Accepted** (2026-10-15)

## Context

The constraint model must say which pairings are permissible and how closeness is
treated. Two related misunderstandings surfaced during grounding on real data.

## Decision

**1. Parent-offspring (buck × daughter) is NORMAL, allowed line-breeding.** It is
standard livestock practice (used to lock in desirable traits), NOT forbidden and
NOT gated behind any last-resort rule. It is scored by the normal r (0.5, the
close tier) like any close pairing.

**2. Only full-sib same-generation (brother × sister) carries the "last resort"
concept** — allowed only when no non-sib buck is feasible for that doe, and
heavily penalized (`penalty_sibling`).

**3. "Feasible" is PERMISSIVE, not prescriptive.** The constraint set (same
strain, not the same rabbit, full-sib-as-last-resort) only defines what is
*biologically permissible*; it does NOT narrow a doe to "the one correct buck."
The optimizer is free to pick very suboptimal pairings if that is the least-bad
option available; every permissible pairing stays on the table and is ranked
lower by scoring, not eliminated.

## Motivation

- Parent-offspring line-breeding is a deliberate trait-locking strategy, not an
  accident to minimize away (see ADR 0011 for the closeness policy).
- An earlier draft wrongly treated parent-offspring as an exclusion, which would
  have forced some does to one buck (e.g. isabelle → willy) and shrunk the
  TAMUK assignment space; the correct rule opens it back up.

## Consequences

- The feasible-buck computation must NOT exclude parent-offspring.
- Kinship tiers: full-sib AND parent-offspring both sit at r≈0.5 (share the tier
  penalty), but eligibility differs — full-sib is last-resort, parent-offspring
  is routine.
- The solver may consider suboptimal-but-permissible pairings.

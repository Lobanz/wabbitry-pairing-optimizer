# ADR 0012: Buck-diversity generated during pairing (not only scored)

**Status:** Accepted (2026-10-15)

**Context**

The multi-start ranked greedy assigns does doe-by-doe with no memory of prior
buck load. With `weight_r = 1.0`, whichever buck is outcross to the most does
in a strain grabs most of them — the Oct-2026 round put 4 of 6 TAMUK does on
Vader. This is the objective working as designed, not a tuning bug.

But it hurts trio quality. A mixed trio = 1 buck + 2 sister-does, cross-strain.
If all 6 TAMUK litters share one sire, the trio-builder has a single TAMUK
sire-line for "the buck" and all buck-kits are siblings. Spreading does across
sires gives 3 distinct lines to compose trios from (operator: "the trios will
probably pair better if there are more bucks involved").

A **solution-level buck-diversity score alone cannot fix this.** It can only
rank whatever assignments the search produced; if every multi-start run
concentrates the same way, the diversity term ranks N identical concentrated
solutions and never sees a spread candidate to promote. Diversity must be
**generated** — made reachable by the search — not just scored afterward.

**Decision**

Add a `[diversity]` config section with two INDEPENDENT levers that make
spread reachable during auto-pairing generation (`_assign_one` /
`_multi_start`), applied per-run, per-strain, to AUTO assignment only (fixed
pairs are excluded from auto pools upstream and unaffected). One shared policy
for both strains.

1. **`max_does_per_buck`** (int, default `0` = off) — hard cap. A buck at the
   cap is removed from candidate list for remaining does in the current run.
   Guarantees spread but is blunt: can force a doe onto her 2nd-best buck, and
   a tight pool (does > bucks × cap) can leave does unbred — which the
   full-solution unbred penalty ranks low, never asserted as a hard error.
2. **`load_penalty`** (float, default `0.0` = off) — soft. A buck's effective
   per-pairing score drops by this amount per doe it already holds in the
   current run. The greedy spreads naturally but can still concentrate when a
   buck is genuinely the only good match — preserves least-bad, and has no
   unbred failure mode.

Defaults: the hard cap is OFF (`0`); the soft penalty is ON by default
(`0.5`) — the operator's settled "soft-only" policy. Existing least-bad
concentration is replaced by soft-driven spread by default; the cap remains
available but OFF. Both knobs interoperate with the shuffled multi-start
search: different per-run doe orders build load differently, so the search
proposes a range of spread assignments for the full-solution score to rank.

**Consequences**

- The solver can now propose (and score) genuinely different, buck-spread
  assignments; a future quality-aware pairability mode (or a distinct-sire
  full-solution term) will have diverse solutions to rank.
- Verified on the real roster (seed 42) across the four variants (base /
  soft 0.5 / cap 2 / both): baseline max load 5 on one buck; soft drops it to
  2 and yields the most distinct sires (6); the cap forces M70 over-spread
  (Zack→2, Opal to her sire Uno) for no sire-diversity gain, so SOFT-ONLY is
  the chosen policy. Genetic quality (sum r, sum_history, no full-sib, no
  unbred) is identical across all four — the variants only differ in which
  buck, not how related.
- Hard-cap failure mode (tight pool unbred) is documented; the cap stays OFF.
- TAMUK buck pool for the Oct-2026 round remains Vader/Willy/Xerces; Willy
  stays active (vigorous, Vader is his eventual replacement).

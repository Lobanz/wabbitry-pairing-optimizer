# Session Resume Handoff

Date: 2026-10-15 (post-Phase 6; Tier-column removal + buck-diversity merged)
Author: Hermes
Purpose: Let the next session resume the wabbitry pairing optimizer cleanly.

## TL;DR

`wabbitry-pairing-optimizer` (GitHub `Lobanz/wabbitry-pairing-optimizer`) is a
**complete, tested, operator-refined** least-bad breeding-pairing tool. Phases
0-6 are merged to `main`. On top of the phased base, two operator-driven
changes merged 2026-10-15:

- **PR #22** — removed the `Tier` column from the markdown pairings table
  (render-only; `pair_type` still in the JSON record).
- **PR #23** — added the `[diversity]` buck-spread policy (soft penalty ON by
  default `0.5`, hard cap OFF by default `0`), ADR 0012.

The tool reads `data/breeders.json` (28 rabbits) + `data/litters/`, solves
least-bad pairings per strain (M70 / TAMUK, never crossed), and writes a
dual-format report (json + markdown) + CSVs + run log to `--output-dir`
(default `out/`).

## Current git / file state

- `main` @ `ed07fd7` (PR #22, Tier column) + PR #23 (buck-diversity).
- ADRs 0001-0012 present in `decisions/`.
- README + SESSION-RESUME refreshed to the current report format + diversity
  policy.
- Default `data/config.toml`: `[diversity] load_penalty = 0.5` (soft ON),
  `max_does_per_buck = 0` (hard cap OFF).

## What the tool does (current report)

`python -m wabbitry_pairing_optimizer --pairs data/fixed_pairs.json --seed 42`
writes to `out/`:
- `wabbitry-report.md` / `wabbitry-report.json` — pairings as a table
  (Buck/Doe/Doe Score/**Related%**/Pair Score/**Warning**), full-solution
  score, and **two schedule tables** (capped at N bucks/day and all-bucks/day;
  no rest days — operator inserts them).
- `kinship-table.csv`, `doe-productivity.csv`, `wabbitry-run.log` (file logging
  in the output dir, not stdout).

Key params: `--seed` (0 = random, positive = reproducible, 42 = tuning),
`--output json|text` (terminal only), `--output-dir`, `--pairs`, `--config`.
Precedence: CLI > config file > defaults.

## Buck-diversity policy (`[diversity]`, operator-settled 2026-10-15)

The multi-start greedy, doe-by-doe with no memory of prior buck load,
concentrated does on the buck outcross to the most of them (Oct-2026: Vader
took 4/6 TAMUK does). Diversity must be **generated** during pairing, not only
scored — a solution-level term can't fix a search that never proposes a spread
assignment.

Two independent levers (one policy across both strains, auto-assignment only):
- **`load_penalty`** (default `0.5`, soft, ON) — a buck's score drops by this
  per doe it already holds; spreads naturally, still lets a buck concentrate
  when it's the only good match. **This is the operator's preferred lever.**
- **`max_does_per_buck`** (default `0` = off, hard cap) — a buck at the cap is
  removed from candidates. Blunt (can force a 2nd-best pair or strand a tight
  pool) — kept but OFF.

Verified (seed 42, four variants): soft spreads TAMUK 2/2/2 and yields the
most distinct sires (6); the hard cap over-spreads M70 (Zack→2, Opal to her
sire Uno) for no diversity gain. Genetic quality (sum r, sum_history, no
full-sib, no unbred) identical across all variants. Hard cap: see ADR 0012.

## Breed data (context, unchanged)

- Roster = 28 rabbits (20 active + 8 culled).
- **M70** (7 does / 3 bucks): bucks yaz (founder outcross — the diversity
  intervention, sires betty/lily/kiki via fixed pairs), zack (= Zeek x Betsy),
  uno (= Zeek x Abigail). Does: abby/amber (= Zeek x Abigail, sisters),
  betty/kiki/lily/maxine (= Zeek x Betsy, sisters), opal (= uno x lily).
- **TAMUK** (6 does / 3 bucks): vader, willy, xerces; does isabelle, fiona,
  ginseng, harmony, iris, jade. Willy stays active this round (vigorous;
  Vader is his eventual replacement).
- **Composite** (vincent) excluded from breeding. Parentage taken at face value
  (no `parentage_uncertain` field anymore).
- M70 bottleneck: every M70 traces to Zeek over two sister-does; **yaz is the
  only M70 outcross** — his line must produce the replacement buck.

## Scoring / model (locked)

- Kinship `r` + founder-sister factor S (ADR 0003). Tiers: outcross(0) >
  line_bred(1) > sibling(5). Parent-offspring and founder-sisters = line_bred;
  only true same-generation full-sibs = sibling (ADR 0004 amendment).
- Both scoring tiers maximize. Per-pairing = `-w_r·r + w_hist·prod - penalty`.
  Full-solution = six weighted components (sum_r negated, negative weights for
  unbred/sibling/schedule penalties). Weights provisional — tune once working.
- Solver: multi-start ranked greedy (min_runs 500 / stall 100), per-strain
  pools, fixed-pair exclusion, `[diversity]` load feedback during generation.
  Pairability = availability-count seam (constant across feasible solutions;
  report value only).

## Open / next items

- **Promote Oct-2026 soft-only round** to permanent `data/` (replace the old
  `data/2026-Oct/` snapshot) — new issue, per operator.
- The `[diversity]` hard cap stays available for future rounds where a hard
  per-buck ceiling is wanted (not the active lever).
- Pairability is a swappable seam; a future quality-aware mode (distinct
  sire-lines) would give the objective a real trio-quality signal.

## Misc / notes

- Network probing of the dev host is off-limits (session constraint).
- Never print token values; multi-PAT via `gh-use-pat.sh status`.
- Operator's workflow: phased implementation, each phase = issue + branch + PR
  + reassessment gate + ADR harvest. Decisions get ADRs, not silence.
- Fixed pairs live in `data/fixed_pairs.json`; pass via `--pairs`.

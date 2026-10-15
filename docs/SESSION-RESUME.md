# Session Resume Handoff

Date: 2026-10-15 (Phase 5 merged; Phase 6 hardening in progress)
Author: Hermes
Purpose: Let the next session resume the wabbitry pairing optimizer cleanly.

## TL;DR

`wabbitry-pairing-optimizer` (GitHub `Lobanz/wabbitry-pairing-optimizer`) is a
**complete, tested, operator-refined** least-bad breeding-pairing tool. Phases
0-5 are merged to `main`; **Phase 6 (hardening/docs/security/close-out) is in
progress on branch `phase/6-hardening`** (issue #13).

The tool reads `data/breeders.json` (28 rabbits) + `data/litters/`, solves
least-bad pairings per strain (M70 / TAMUK, never crossed), and writes a
dual-format report (json + markdown) + CSVs + run log to `--output-dir`
(default `out/`).

## Current git / file state

- `main` @ `4e85138` (Phase 5 merged via PR #12, squash).
- Current branch: `phase/6-hardening` (new, issue #13).
- ADRs 0001-0011 all present in `decisions/` (harvest complete).
- README refreshed (Phase 6), documenting full CLI + report format.
- Phase 6 in-flight on the branch:
  - `config.py`: added `OutputConfig` field validator rejecting path-traversal
    output filenames (absolute / `..` / separator) -> ValueError -> wrapped to
    ConfigError by `load_config`.
  - `tests/test_security.py`: traversal-guard tests + empty/single-buck edge
    cases (mutation-verified: guard-dropped -> FAIL).
- Test status before in-flight Phase 6 edits: 51 passing, check.sh clean.
  Re-run the gate after Phase 6 edits.

## What the tool does (final report)

`python -m wabbitry_pairing_optimizer --pairs data/fixed_pairs.json --seed 42`
writes to `out/`:
- `wabbitry-report.md` / `wabbitry-report.json` — pairings as a table
  (Buck/Doe/Tier/**Related%**/Score/**Warning**), full-solution score, and
  **two schedule tables** (capped at N bucks/day and all-bucks/day; no rest
  days — operator inserts them).
- `kinship-table.csv`, `doe-productivity.csv`, `wabbitry-run.log` (file logging
  in the output dir, not stdout).

Key params: `--seed` (0 = random, positive = reproducible, 42 = tuning),
`--output json|text` (terminal only), `--output-dir`, `--pairs`, `--config`.
Precedence: CLI > config file > defaults.

## Breed data (context, unchanged)

- Roster = 28 rabbits (20 active + 8 culled).
- **M70** (7 does / 3 bucks): bucks yaz (founder outcross — the diversity
  intervention, sires betty/lily/kiki via fixed pairs), zack (= Zeek x Betsy),
  uno (= Zeek x Abigail). Does: abby/amber (= Zeek x Abigail, sisters),
  betty/kiki/lily/maxine (= Zeek x Betsy, sisters), opal (= uno x lily).
- **TAMUK** (6 does / 3 bucks): vader, willy, xerces; does isabelle, fiona,
  ginseng, harmony, iris, jade.
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
  pools, fixed-pair exclusion. Pairability = availability-count seam (constant
  across feasible solutions; report value only).

## Phase 6 remaining checklist (issue #13)

- [x] CLI polish: `--help`/`--version`/error paths emit per `--output`.
- [x] ruff S (bandit) clean.
- [x] Path-traversal guard on output filenames + tests.
- [ ] Edge cases candidate: all-sibling round (not yet added).
- [ ] Full check.sh/test.sh green with Phase 6 edits.
- [ ] Commit Phase 6, PR, operator close-out review (incl. roll-up notes).

## Misc / notes

- Network probing of the dev host is off-limits (session constraint).
- Never print token values; multi-PAT via `gh-use-pat.sh status`.
- Operator's workflow: phased implementation, each phase = issue + branch + PR
  + reassessment gate + ADR harvest. Decisions get ADRs, not silence.
- Fixed pairs live in `data/fixed_pairs.json`; pass via `--pairs`.

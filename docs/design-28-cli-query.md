# Design — CLI ad-hoc query + ranked best-pairings (issue #28)

Status: **design proposal for the reassessment gate — no implementation yet.**
Operator rules on the open decisions (§8) before any code.

## 1. Problem

Today, answering a question like "is Uno equally suitable for Abby, Amber, or
Opal?" means writing a throwaway probe script against kinship + scoring, or
re-running the solver with a hand-edited `fixed_pairs.json`. Both are manual
and error-prone. The operator wants the CLI to answer ad-hoc breeding questions
directly, with every number the optimizer uses — not a guess-friendly subset.

## 2. Requirements

- **R1 — Pair query:** arbitrary `sire:dam` pairs → a FULL metric row per pair.
- **R2 — Ranked modes:** best does for a buck, best bucks for a doe.
- **R3 — Fixed-pair override** for a full round without touching the committed
  `data/fixed_pairs.json`.
- **R4 — Conventions:** emission per `--output json|text`; NO solving in
  R1/R2; breeding pools are never crossed (same-strain default).

## 3. Metric payload (per queried pair)

Every field already exists in the codebase — the query assembles, never
recomputes new scoring:

| Field | Source |
|---|---|
| r (raw) + Related % (r×100) | `kinship.coancestry_matrix_r` (S from config) |
| relationship kind (`full_sib`/`parent_offspring`/`founder_sister`/`other`) | `kinship.relationship_kind` |
| tier (`outcross`/`line_bred`/`sibling`) + tier penalty | `kinship.tier_for_pair` + scoring tier penalty |
| `score_r`, `score_doe_history`, final per-pairing score | `scoring.per_pairing_score` (weights from config) |
| doe productivity index | `productivity.doe_production_scores` |
| productivity detail — own litter count, own score, consistency, trimmed avg size, blend weight `w_own`, dam index | **new structured record (§5)** |
| breed label (full, e.g. `M70 NZW`) + strain + fixed/culled flags | roster |
| warnings | relationship-based only (`full-sibling`, `parent-offspring`) |

**Buck-load warnings are NOT in query mode** (`N does on one buck` needs a
solved round for context). If wanted, they belong to ranking a candidate round,
not a bare pair query.

## 4. CLI surface (options)

**Option A — flags on the existing flat command (recommended):**

```
python -m wabbitry_pairing_optimizer --query "uno:abby, uno:amber, uno:opal"
python -m wabbitry_pairing_optimizer --rank "buck:uno" [--sort r|score|productivity] [--limit N]
python -m wabbitry_pairing_optimizer --rank "doe:opal" [--sort ...] [--limit N]
python -m wabbitry_pairing_optimizer --pairs "yaz:abby,yaz:amber,yaz:opal"   # inline fixed-pair override
```

- `--query` / `--rank` take over immediately (no solving), then exit.
- `--sort` default = final score (r ascending for `r`); `--limit` default = all.
- `--all-strains` exposes cross-strain candidates (flagged, never default).
- `--pairs` accepts a path **or** an inline `sire:dam,...` spec (§6).

**Option B — subcommands** (`query`, `rank`, `solve`): cleaner namespace but a
real CLI-contract refactor of the flat design §8 shape. Reject for now; note as
a future option if the CLI keeps growing modes.

**Recommend A** — minimal contract change, reuses the existing emission path.

## 5. Productivity detail record (finding + proposal)

`doe_production_scores` returns only the index; the components the issue asks
for (own score, consistency, trimmed avg litter size, `w_own`, dam index,
own-litter count) are computed *inside* `productivity_index` and discarded.

Proposal: add a structured helper (e.g. `productivity_detail(...) ->
ProductivityDetail`) that returns the components; `doe_production_scores`
keeps its index contract untouched (solver + report unchanged). The query
payload carries the detail; scoring behavior does not change.

## 6. Fixed-pair default (finding)

The CLI applies fixed pairs **only when `--pairs` is passed** — a bare run
currently solves with NO fixed pairs (`yaz→betty/lily/kiki` unlocked).
`data/fixed_pairs.json` is never auto-loaded, despite being the committed
default.

Proposal: when `--pairs` is absent, default to `data/fixed_pairs.json` (CLI
flag still overrides; inline spec supported). This changes bare-run behavior —
flagged as a likely fix, but operator to confirm.

## 7. Module shape + DAG

- New `query.py` — **pure** (no I/O): pair metrics, ranking, and the
  file-vs-inline `--pairs` parser. Deps: kinship, productivity, scoring,
  models, config (same DAG tier as existing domain modules).
- `__main__.py` — add flags; route `--query`/`--rank` before the solve path.
- Query text rendering lives in `query.py` (own concern); `render.py` remains
  round-artifact-only.
- Tests: `tests/test_query.py` (anchored metric values, e.g. `uno×abby` =
  r 0.50 sibling, final −1.400; rank order; strain filtering; inline `--pairs`
  parsing).

## 8. Open decisions (operator)

- [ ] CLI grammar: Option A flags (recommended) vs Option B subcommands
- [ ] Default `--pairs` to `data/fixed_pairs.json` when flag absent? (recommend yes)
- [ ] Rank candidates: same-strain non-culled by default, fixed-pair rows shown + flagged, cross-strain only via `--all-strains` (recommended)
- [ ] `--sort` default = final score; `--limit` default = all
- [ ] Productivity detail as a structured record (recommended) — confirm
- [ ] Text row: same columns as the round report row (buck, doe, breed×2, r%, pair score, warning) — confirm

## 9. Out of scope

- No kinship / scoring / productivity-model changes (the payload is assembled
  from existing outputs + the §5 detail exposure).
- No round-artifact / report changes.
- Buck-load warnings (need a solution context).

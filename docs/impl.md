# Implementation Plan — Wabbitry Pairing Optimizer

Status: **Draft for operator review.** Gate: after review, the operator gives an
explicit 'go' before any code is written (matches the standing design-first
protocol).

## ESL conformance

This project aligns with the ESL engineering-standards library
(`~/projects/eslbundle/standards/`, `AGENT-STANDARDS.md`). The Python module
(`languages/python.impl.md`, status **Active (partial)**) applies. Conformance
obligations for this implementation:

**Tooling (already configured in `pyproject.toml`):**
- `ruff` = formatter + linter (no black/flake8/isort/pydocstyle). Rule sets
  selected: `E,F,W,I,N,D,ANN,B,UP,S`. `ruff format --check` + `ruff check` in
  the project scripts.
- `mypy --strict` (strict from first commit; **no loose-then-tight migration**).
- `pytest` as test runner; production code never imports `pytest`.
- **Commands wrapped in project scripts** — `scripts/check.sh` / `scripts/test.sh`
  are the canonical entry points (pre-commit + CI invoke them; humans run them
  before push).

**Type hints:** every public function/method/attribute typed; `Any` requires a
`# REASON:` comment; parameters use the most general protocol type (`Sequence`,
`Mapping`) while returns use the concrete type.

**Docstrings:** Google format; docstring required on every public module, class,
method, function; module docstring on every module (the Python expression of the
module-headers rule). Rendered by ruff `D` rules.

**Imports:** grouped stdlib → third-party → local, alphabetized (`I`); absolute
across packages; no star imports (`F403/F405`).

**Module structure:** one concern per file (`one-concern-per-file` — reinforces
the dependency-DAG principle); `__all__` when the public API is a curated subset;
`__init__.py` re-exports API or is empty (no implementation).

**No magic literals** (Python expression): named constants in
`SCREAMING_SNAKE_CASE` with `Final`; related constant sets as `Enum`; compound
constants as `frozen` dataclasses. (Config values live in `config.toml`, not
code — design §9.)

**Error handling:** raise exceptions, never error codes/Result-tuples; a
project base exception class; custom classes per error category; bare `except`
forbidden; broad `except Exception:` needs `# REASON:`; re-raise with `from`.

**Logging:** `logger = logging.getLogger(__name__)` at module top; structured
emissions via `extra`, not string formatting in the message (`ruff G004`);
never log secrets.

**Testing:** `test_<unit>_<scenario>_<expected_outcome>` naming;
`@pytest.mark.parametrize` for input/output tables; fixtures declare non-function
scope explicitly; `tests/` mirrors source structure.

**Python-specific security:** no `eval`/`exec`/`compile` on untrusted input;
no pickle deserialization (use json + pydantic); no `subprocess(..., shell=True)`
with user input; `secrets` (not `random`) for any security-sensitive value;
`with` context managers for all resources.

**Stubs / partial status:** the Python module has stubbed sections (async,
concurrency, class design, runtime validation, web, ORM, packaging, performance).
Where a stubbed topic would be load-bearing, follow `core/engineering-principles:
ask-before-assume` — fall back to community convention or ask the operator.

**Where this bites per phase:** Phase 0 confirms tooling+models conform; each
later phase's code is written against these rules, and `scripts/check.sh`
(ruff S-bandit + mypy strict) is the mechanical gate every phase must pass
before its reassessment gate.

## Operating principles (operator-set, non-negotiable)

- **Phases are reassessment gates, not checkpoints.** Between phases — and inside
  a phase when something surprises us — we stop and re-evaluate what was learned:
  change the design, change direction. Not an opportunity to satisfice and plow
  toward a suboptimal solution.
- **Quality, maintainable, documented, secure code over fast code.** Benchmarks
  are not the goal; correctness, auditability, and maintainability are.
- **Impl surfaces things design can't see.** That is expected and welcome. Any
  conflict between impl reality and the design becomes a **reassessment point**
  decided jointly with the operator — not a silent workaround.
- **Decoupled core, thin wrappers** (§11): a mid-course direction change stays
  cheap because the solver is a pure function and rendering/CLI are thin shells.
- **One concern per file; dependency DAG acyclic** (operator-set). No circular
  imports.
- **No magic constants**: every tunable lives in `data/config.toml` (design §9).
- **Tests, docs, and security are first-class per phase**, not bolted on at the
  end. The repo tooling (ruff incl. security `S`, mypy strict, pytest) runs in
  `scripts/check.sh` / `scripts/test.sh` and gates each phase.

## Module DAG (target layout; built across phases)

```
models.py                 # pydantic: Breeder, Pairing, PairingReport, Solution, Config
  ▲
__main__.py  ── render.py ── solve.py ── kinship.py ── recipe.py ── load_breeders.py
                 │            │            │              │
                 │           config.py ────┘              load_litters.py
                 └───────────── productivity.py ──────────┘
                                   ▲
                              pairability.py
```

Dependencies always flow one way (no cycles):
- `models.py` — no deps.
- `config.py`, `load_breeders.py`, `load_litters.py` — depend only on models.
- `recipe.py` — models + load_breeders (derives/validates recipe vectors).
- `kinship.py` — models + recipe + config (r + founder-sister factor S + tiers).
- `productivity.py` — models + load_litters + config (doe productivity index).
- `pairability.py` — models + solve output + config (swappable metric mode).
- `solve.py` — models + config + kinship + productivity (+ pairability seam).
- `render.py` — models + solve's Solution (text/json/md + output-dir artifacts).
- `__main__.py` — CLI arg parsing + wiring (only place that knows all modules).

## Phase 0 — Foundations & reassessment discipline

**Goal:** stand up the skeleton, the toolchain gates, and the test harness so every
later phase runs against a quality bar. Validate the two-layer CLI convention.

Deliverables:
- Confirm `pyproject.toml` / ruff / mypy / pytest / `scripts/check.sh` /
  `scripts/test.sh` run clean on the current scaffold (models.py exists).
- `models.py` — finalize pydantic models to match design §2/§7/§8:
  `Breeder` (lowercase name, breed, gender, culled, founder, sire, dam,
  founder_sisters, recipe), `Pairing` (sire, dam, kinship,
  penalty, scores, pair_type), `Solution` (pairings, per-pairing scores,
  full-solution score components, schedule, pairability), `Config`.
- `config.py` — load `data/config.toml` into `Config`; TOML section mapping
  (§9). Invalid config → clear structured error.
- `data/config.toml` — the operator-policy values (already drafted).
- Seed: `__init__.py`, a trivial first test proving the harness is green.

**Reassessment gate (mandatory):** operator reviews the running toolchain + the
finalized models against design §2/§7/§8. Any model-shape or config-contract
disagreements are fixed NOW (cheapest), before algorithms depend on them.

Exit criteria: `scripts/check.sh` and `scripts/test.sh` pass; config loads; models
match the design; the two-layer `--output json|text` emission convention is
spec'd for `__main__.py` (even if not yet wired to real logic).

## Phase 1 — Data loading, recipe, kinship (the genetic core)

**Goal:** get real r values flowing end-to-end, because the whole solver's
behavior rests on whether the kinship tables are correct. This is the highest-risk
correctness component — reassessment here is most valuable.

Deliverables:
- `load_breeders.py` — load `data/breeders.json` (28 rabbits, lowercase), validate
  FKs resolve, recipes sum to 1.0, no duplicate names. Reject/fail loudly on bad
  data (not silent fixes).
- `load_litters.py` — load `data/litters/*.json` (7 files, 42 litters), validate
  dam/sire resolve, LF only.
- `recipe.py` — derive/validate recipe vectors; confirm stored recipes match the
  half-parent recursion; founder = self-signed root. (Recipes are stored, so this
  is verification + a derived fallback.)
- `kinship.py` — implement r(A,B) + founder-sister factor S (§5), tier table with
  configurable penalties and `outcross_r_max`. Unit-test against the verified
  anchor values from ADR 0003 (yaz×betty=0.0, betty×lily=0.5, betty×abby=0.375 @
  S=0.5, abigail×betsy=S=0.5, betty×self=1.0, no two distinct > 0.5).
- A standalone kinship-table dump (dev tool) so the operator can eyeball r values
  on the real 28-rabbit roster against expectations.

**Reassessment gate (mandatory):** show the operator the real kinship table for
the actual breeders. Are the r values as expected? Does the founder-sister factor
behave sensibly on real data? Any design correction here propagates everywhere, so
this is the most important gate in the plan. Direction changes are cheapest now.

Exit criteria: r tables verified against the ADR anchors; operator is satisfied
the kinship model reflects reality; `scripts/check.sh` / `test.sh` green.

## Phase 2 — Doe productivity index

**Goal:** compute `doe_history` from the litters so the per-pairing and
full-solution scorers have the production signal.

Deliverables:
- `productivity.py` — doe productivity index per design: `size_weight*avg(litter) +
  consistency_weight*consistency`, **outliers trimmed** (config method iqr/zscore),
  blended with mother's index by `own_count/(own_count+evidence_K)`.
- Handle thin data honestly: n=0/n=1 does lean on mother; document maxine case.
- Unit tests: betty/lily/kiki/maxine, Betsy-vs-Abigail sanity, mother-blend edges.
- A doe-productivity table dump for operator inspection.

**Reassessment gate:** operator reviews the productivity index values on real
does. Does the size/consistency blend + mother-evidence smoothing feel right?
Adjust weights/method in config (they're all config knobs) without code change
where possible.

Exit criteria: productivity index values operator-approved; edge cases tested;
toolchains green.

## Phase 3 — Pairing + full-solution scoring (the objective function)

**Goal:** implement the two-tier scoring (design §8) so we can score *any*
assignment, before we can produce assignments. This decouples "how good is a
solution" from "how do we find one" — letting us validate the objective against
hand-built example solutions first.

Deliverables:
- `per_pairing_score()` — r + doe_history (weights from config).
- `full_solution_score()` — the six weighted components from §8:
  1. sum-r, 2. sum-doe_history, 3. unbred penalty, 4. sibling penalty,
  5. schedule length (batch/calendar model), 6. pairability (swap-mode seam).
- `pairability.py` — the mixed-pair availability-count metric (§4), plus the
  config selectable mode; the `pairability(solution)->float` seam documented.
- `Schedule length` computation — the batch (≤4-buck) calendar model, pure function.
- Unit tests for each component, incl. hand-constructed solutions where the correct
  score is known by inspection.
- Wire `Config` weights → all scorers (no magic constants anywhere).

**Reassessment gate:** walk through the component scores on 2-3 hand-built example
solutions with the operator. Does the weighted composite reflect what you'd judge
by eye? Tune weights in config. **The objective function is the heart of the tool —
this gate is where the operator's real-world priorities most need to be heard.**

Exit criteria: scoring components correct + operator-approved weights; schedule and
pairability seams work; check/test green.

## Phase 4 — Assignment solver (multi-start ranked greedy)

**Goal:** produce full solutions. This is where the earlier components compose.

Deliverables:
- `solve.py` — the fixed-pairs + multi-start ranked greedy (design §6):
  - fixed-pairs pass (exclude both sides; compute full rationale scores; keep in
    model; include in output).
  - shuffle ALL pools each run.
  - per-doe greedy assignment using per-pairing score; sibling as last resort only.
  - full-solution scoring per candidate.
  - **stall-based termination**: min-runs gate + stall-limit (config), comparison
    function on Solution for immediate new-winner detection; fixed seed option for
    reproducibility.
- `Solution` comparison function (`__lt__`/key) so ranking and winner-tracking are
  trivial.
- Tests: deterministic under a fixed seed; respects hard constraints (strain, culled,
  fixed-pair exclusion, sibling-last-resort); produces an assignment for all active
  does; reproduces the Yaz fixed pairs; multi-run stability.

**Reassessment gate (major):** run the solver on the full real roster. Show the
operator the winning solution + its score breakdown + the runner-up alternatives.
Does the result reflect your breeding priorities? Is the fixed-pair (Yaz) handling
right? Does schedule/pairability nudge the result sensibly? This is the first time
the whole tool produces an actual answer — expect genuine reassessment here.

Exit criteria: correct, constraint-respecting full solutions on real data; operator
judges the output directionally correct; check/test green.

## Phase 5 — Rendering & output-dir artifacts

**Goal:** the dual-format human/agent deliverables (design §8) and the two-layer
CLI.

Deliverables:
- `render.py` — text/json/md renders of a `Solution`:
  - json: structured result incl. kinship + doe-productivity tables as data.
  - md: comprehensive human report (pairings + per-pairing scores, solution-score
    components, kinship table, doe-productivity table, schedule, pairability).
  - text: quick human eyeball at the terminal.
- `--output-dir <dir>` writes `wabbitry-report.json`, `wabbitry-report.md`,
  `kinship-table.csv`, `doe-productivity.csv` (names from config `[output]`).
- The pairability metric is the **availability-count** itself (no "real trio
  optimizer" is available on this repo to back it with an exact trio count —
  that tool is a separate project). The `pairability(solution)->float` swappable
  seam is the documented future path: when/if the trio optimizer lands on
  this repo, its output can replace the availability-count body via the seam +
  config `mode`, without touching the solver.
- Two-layer CLI: `--output json|text` controls ALL terminal emissions (help,
  version, errors); result artifacts always written to output-dir in both json+md.

**Reassessment gate:** review a sample md report + the output-dir contents with the
operator. Is the human report genuinely comprehensive and readable? Is the json
useful for the agent/software consumer?

Exit criteria: dual-format output correct; output-dir artifacts written; CLI
convention honored; report operator-approved; check/test green.

## Phase 6 — Hardening, docs, security review, close-out

**Goal:** make it solid and durable, not just working.

Deliverables:
- `__main__.py` wiring polished; `--help`, `--version`, error paths emit per the
  `--output` convention (structured json for agents).
- Security review pass: ruff `S` (bandit) clean; no secrets/network; validate
  untrusted input files (path traversal off the config `output_dir`/filenames —
  since filenames are operator-supplied config, guard against absolute/`..` paths
  escaping the intended dir); data files validated on load.
- Docs: complete README (usage, config reference, output description),
  SESSION-RESUME.md refreshed to reflect the locked design, ADRs current.
- Tests: full suite green; edge cases (empty pools, single-buck, all-sibling) added.
- Final operator review of the entire repo.

**Reassessment gate (close-out):** full walkthrough. Anything learned across all
phases that should change the design? Any roll-up/future-proofing notes for the
larger system (§11)?

Exit criteria: secure, documented, tested, operator-approved; `check.sh`/`test.sh`
green; readiness for a first real run.

## Sequencing rationale (why this order)

- **Phase 0/1 first**: validate the data model + kinship (the genetic truth) before
  anything depends on them; the highest-risk correctness pieces get the earliest,
  cheapest reassessment.
- **Scoring (Phase 3) before the solver (Phase 4)**: score by hand-built solutions
  first, so the objective is operator-approved before we optimize against it. A
  wrong objective optimized is worth nothing.
- **Solver → rendering → hardening**: once a correct solution exists, present it,
  then secure/polish. This keeps each phase's reassessment focused on one kind of
  learning.

## Definition of done

All phases complete with their reassessment gates passed; operator has given an
explicit 'go' at the start and been an active reviewer at each gate; the tool
produces an operator-approved, documented, tested, secure least-bad pairing report
for the fall round.

## Git / issue workflow (operator-set)

- **Each phase** = its own **issue + branch + PR**:
  - a GitHub **issue** documenting the phase's goal, deliverables, and
    reassessment gate;
  - a dedicated **branch** (`phase/<n>-<slug>`) per phase;
  - a **PR** referencing the issue on completion, merged after the reassessment
    gate and operator review.
- **Design changes / feature additions / direction changes** also get their own
  **issues** documenting them — from here on nothing is done silently. An
  issue is the audit record for every decision and change.
- **Harvest decisions into `decisions/` ADRs** so the audit trail is complete.
  The three existing ADRs (0001 Yaz strategy, 0002 lowercase names,
  0003 r-coefficient) cover part of the design; the design session also decided
  things not yet ADR'd — the two-tier scoring model, the pairability
  (mixed-pair availability) metric, the schedule/calendar model, the TOML
  config architecture, the module DAG, and this git/issue workflow. **Baseline
  step (Phase 0): write the remaining ADRs** so every locked decision has a
  record before implementation code accretes onto them.
- This keeps a per-change attribution trail (matching the operator's
  audit-trail value) and makes each phase's learning a reviewable unit.

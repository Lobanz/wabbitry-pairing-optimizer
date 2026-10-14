# ADR 0008 — Module architecture: one concern per file, dependency DAG

Status: **Accepted** (2026-10-15)

## Context

This code is likely to be rolled up into something bigger eventually ("code
lives in the future"). The structure must stay decoupled so direction changes
stay cheap and the core is reusable.

## Decision

- **One concern per file; dependencies form a DAG (acyclic).**
- Target layout:
  - `models.py` — root, no deps (pydantic data objects).
  - `config.py`, `load_breeders.py`, `load_litters.py` — depend only on models.
  - `recipe.py` → `kinship.py`; `productivity.py`; `pairability.py` — each a
    domain concern with narrow deps.
  - `solve.py` — the **pure, decoupled core**: `(roster, fixed_pairs, config) ->
    Solution` with no I/O and no rendering.
  - `render.py` — text/json/md renders of a `Solution`.
  - `__main__.py` — CLI wiring only (the single place that knows all modules).
- No circular imports, ever.

## Motivation

- One concern per file means a change to kinship scoring touches only
  `kinship.py`, not the solver or report.
- The pure `solve` core is the future-proof (roll-up) artifact: it has no I/O,
  so it can be embedded, served, or reused without a terminal.
- Acyclic deps keep the modules independently testable.

## Consequences

- A mid-course direction change (e.g. replace the pairability metric) is a
  one-module change plus a config `mode` (see ADR 0005).
- Tests target single modules; no cross-module coupling to untangle.
- The scaffold's old `pairing.py` (mixing kinship + assignment + I/O) was
  removed; its responsibilities moved to the DAG modules.

# ADR 0007 — TOML config architecture + precedence

Status: **Accepted** (2026-10-15)

## Context

The optimizer has many tunable, opinion values: kinship thresholds, doe
productivity weights, scoring weights (both tiers), tier penalties, pairability
mode, optimization knobs, and output-artifact settings. These should not be
scattered magic constants in code — they are operator policy and must be visible,
tweakable, and auditable in one place.

## Decision

All tunable/opinion values live in a **TOML config file** (default
`data/config.toml`) with structured sections:

- `[kinship]` — sister_factor, outcross_r_max
- `[productivity]` — size_weight, consistency_weight, evidence_k, outlier_method,
  outlier_threshold
- `[scoring.per_pairing]`, `[scoring.tier_penalty]`, `[scoring.full_solution]` —
  the two-tier scoring weights and tier penalties
- `[pairability]` — mode (selectable metric)
- `[optimization]` — min_runs, stall_limit, seed, buck_batch_capacity
- `[output]` — output_dir, result filenames, log file settings

**Precedence (top wins): CLI params → config-file values → reasonable built-in
defaults.** A param resolves: an explicit CLI flag overrides the config file,
which overrides the built-in default. The built-ins are sensible starters we can
fine-tune later.

**`--output` (terminal emission format) is NOT a config param.** It only governs
the stdout interface and lives solely at the CLI. By contrast `[output]` holds
the *result-artifact* settings (where/names files are written) — which is
operator policy and belongs in config.

## Motivation

- One authoritative place for every policy knob; no magic constants anywhere.
- Auditable: the report carries the weights used (see ADR 0004).
- Precedence lets the operator run one-off overrides without editing the file.

## Consequences

- `config.py` loads TOML into a typed pydantic `Config`; invalid config surfaces
  a clear `ConfigError`.
- Changing behavior is a config edit, not a code change, in the common case.

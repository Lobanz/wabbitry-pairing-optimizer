# 2026-10 — Official breeding-round snapshot

This directory is the **official, version-controlled record** of the
October-2026 breeding round, generated under the settled **soft-only**
buck-diversity policy (ADR 0012). It is the output of the Wabbitry Pairing
Optimizer, promoted here from the gitignored `out/` build dir so the run is
committed history.

## Run facts

- **Generated**: 2026-10-15
- **Seed**: `42` (deterministic)
- **Inputs**: `data/breeders.json` + litters from `data/litters/` via
  `--pairs data/fixed_pairs.json --config data/config.toml`
- **Diversity policy**: soft-only — `[diversity] load_penalty = 0.5`
  (hard cap `max_does_per_buck = 0`, off). Spreads does across sires so trios
  have multiple sire-lines.
- **Result**: 13 pairings, final score `+47.94`, 4 days, no unbred does.
  TAMUK spread 2/2/2 across Vader/Xerces/Willy (was 4/1/1 baseline);
  M70 untouched (Zack 3, Uno 1 + Yaz fixed 3).

## Files

| File | Contents |
|------|----------|
| `wabbitry-report.md` | human report: score table, pairings table (Doe Score / Pair Score / Related% / Warning), two schedule tables |
| `wabbitry-report.json` | structured record incl. both schedule calendars |
| `kinship-table.csv` | kinship r matrix |
| `doe-productivity.csv` | doe productivity index (Doe Score) |
| `wabbitry-run.log` | run log |

The pairings table has **no Tier column** (removed PR #22); the relationship
tier still lives in the JSON report and drives the Warning column.

## Reproducibility

This snapshot is fully reproducible from committed inputs + the committed
`data/config.toml` (soft-only default):

```bash
python -m wabbitry_pairing_optimizer \
  --config data/config.toml --pairs data/fixed_pairs.json --seed 42 \
  --output-dir <target-dir>
```

Same tool version + same inputs + `--seed 42` regenerates these exact
artifacts. The prior baseline snapshot (Vader ×4) was superseded and removed
(this run, recoverable via git history).

## Note

`out/` remains the working output dir (gitignored). Each future breeding round
gets its own dated snapshot dir here (e.g. `2027-01/`) as official history.

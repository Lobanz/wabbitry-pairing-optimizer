# 2026-Oct — Official breeding-round snapshot

This directory is the **official, version-controlled record** of the
October-2026 breeding round. It is the output of the Wabbitry Pairing
Optimizer, moved here from the gitignored `out/` build dir so the run is
committed history.

## Run facts

- **Generated**: 2026-10-15
- **Seed**: `42` (deterministic)
- **Inputs**: `data/breeders.json` + litters from `data/litters/` via
  `--pairs data/fixed_pairs.json`
- **Result**: 13 pairings, final score `+47.94`, 4 days, no unbred does

## Files

| File | Contents |
|------|----------|
| `wabbitry-report.md` | human report: score table, pairings table (Doe Score / Pair Score / Related% / Warning), two schedule tables |
| `wabbitry-report.json` | structured record incl. both schedule calendars |
| `kinship-table.csv` | kinship r matrix |
| `doe-productivity.csv` | doe productivity index (Doe Score) |
| `wabbitry-run.log` | run log |

## Reproducibility

This snapshot is fully reproducible from the committed inputs:

```bash
python -m wabbitry_pairing_optimizer \
  --pairs data/fixed_pairs.json --seed 42 --output-dir out/
```

Same version of the tool + same inputs + `--seed 42` regenerates these exact
artifacts.

## Note

`out/` remains the working output dir (gitignored). Each future breeding round
gets its own dated snapshot dir here (e.g. `2027-Jan/`) as official history.

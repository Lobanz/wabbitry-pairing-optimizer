# Wabbitry Pairing Optimizer

Computes least-bad buck x doe breeding pairings for Wascally Wabbitry
(Hazel Green, AL), given the breeding stock and their parentage.

This is the **least-bad pairing** tool (decides *which buck breeds which doe*),
distinct from the existing trio-from-litters optimizer (which groups kits into
saleable trios). The real trio optimizer is not available here; pairability is
a pure availability-count seam (see `decisions/0005`).

## Why this exists

M70 and TAMUK NZW lines have been kept separate forever to retain hybrid vigor
for mixed sales. M70s are now nearly impossible to source, so the M70 pool is a
genetic bottleneck (descends from founder buck Zeek and his two sister-does).
This tool respects the strain separation while picking the least-related
available mates within each pool.

## Constraints

- **M70 x M70 only; TAMUK x TAMUK only** — never cross.
- **Composite strain** (e.g. Vincent) excluded from breeding. TAMUK NZW bucks
  in the pool: vader, willy, xerces.
- **Culled rabbits** excluded as breeding candidates (kept for pedigree ref).
- **Yaz sires betty/lily/kiki** via fixed pairs (his M70 blood is the only
  non-Zeek option; M70 source wabbitry is closed).
- **Kinship tiers**, best to worst: outcross > line-breeding > siblings.
  Parent-offspring and founder-sisters count as line-breeding (allowed);
  only true same-generation full-siblings carry the heavy penalty and are a
  last resort.
- **Fixed pairs** (operator pre-decided) are always included and are not
  flagged as warnings.

## Usage

```bash
python -m wabbitry_pairing_optimizer <breeders.json> [options]
```

Defaults read `data/breeders.json`, `data/config.toml`, and litters from
`data/litters/`. Copy the canonical roster from
`~/projects/wabbitry-receipt/data/breeders.json` when stock changes.

### Options

| Flag | Meaning |
|------|---------|
| `breeders` | path to `breeders.json` (positional) |
| `--pairs FILE` | pre-decided fixed pairings JSON: `[{"sire","dam"}, ...]` |
| `--config FILE` | TOML config (default `data/config.toml`) |
| `--seed N` | PRNG seed override; `0` = seedless/random, positive = reproducible (use e.g. `42` while tuning weights) |
| `--output json\|text` | terminal emission format (default `json`); does NOT change the written artifacts |
| `--output-dir DIR` | artifact output directory (default from config, `out/`) |

Precedence: **CLI flags > config file > built-in defaults.**

### Example

```bash
python -m wabbitry_pairing_optimizer --pairs data/fixed_pairs.json --seed 42
```

Writes to `out/` (see below). Seeded runs are reproducible: same inputs + seed
give the same round every time.

## Output artifacts (written to `--output-dir`)

| File | Contents |
|------|----------|
| `wabbitry-report.json` | structured record: seed, score, pairings, both schedule calendars, kinship + productivity tables |
| `wabbitry-report.md` | human report: score table, pairings table, two schedule tables |
| `kinship-table.csv` | r matrix (canonical sorted pair -> r) |
| `doe-productivity.csv` | doe name -> productivity index |
| `wabbitry-run.log` | run log (JSON-lines or text per config), in the output dir, not stdout |

### Report: pairings table

Each pairing shows **Buck x Doe** (title-cased), tier, **Related%** (kinship
`r * 100`), score, and a **Warning** column:

- `full-sibling` — true same-generation full siblings (heavy penalty, last resort)
- `parent-offspring` — line-breeding a buck to its own offspring
- `N does on one buck` — one buck servicing more than 2 does in the round

Fixed (operator-decided) pairs are never flagged.

### Report: schedule tables

Two day-batch calendars (no rest days — the operator inserts them):

- **capped at N bucks/day** — at most `buck_batch_capacity` (default 4) distinct
  bucks breed per day
- **all bucks/day** — every eligible buck breeds each day (for running 2
  batches/day to compress the round)

Both are also present in the JSON report (`schedule_capped`, `schedule_all_bucks`).
With the current roster both run 4 days: Vader (4 does) is the single-buck floor.

## Config

`data/config.toml` holds every tunable (kinship tiers, productivity formula,
scoring weights, optimization params incl. `min_runs`/`stall_limit`/`seed`/
`buck_batch_capacity`, and `[output]` artifact policy). See `docs/design.md` §9.

## Development

```bash
python -m pytest          # run tests
scripts/check.sh          # ruff format + ruff check + mypy (static checks)
scripts/test.sh           # pytest
```

Config output-artifact filenames are validated against path traversal at load;
data files are validated on load.

## ESL Compliance

This project follows the engineering standards in the shared
[eng-std-lib bundle](/home/hermes/projects/eslbundle/standards/AGENT-STANDARDS.md).

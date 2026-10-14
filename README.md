# Wabbitry Pairing Optimizer

Computes least-bad buck x doe breeding pairings for Wascally Wabbitry
(Hazel Green, AL), given the breeding stock and their parentage.

This is the **least-bad pairing** tool (decides *which buck breeds which doe*),
distinct from the existing trio-from-litters optimizer (which groups kits into
saleable trios).

## Why this exists

M70 and TAMUK NZW lines have been kept separate forever to retain hybrid vigor
for mixed sales. M70s are now nearly impossible to source, so the M70 pool is a
genetic bottleneck (descends from founder buck Zeek and his two sister-does).
This tool respects the strain separation while picking the least-related
available mates within each pool.

## Constraints

- **M70 x M70 only; TAMUK x TAMUK only** — never cross.
- **Composite strain** (e.g. Vincent) excluded from breeding.
- **Culled rabbits** excluded as breeding candidates (kept for pedigree ref).
- **Yaz sires at least 2 M70 litters** (his offspring were sold out last round).
- Kinship tiers, best to worst: outcross > line-breeding > siblings.
  Sibling pairings carry a heavy penalty and are used only as a last resort.

## Usage

```bash
python -m wabbitry_pairing_optimizer <breeders.json>
# or default path:
python -m wabbitry_pairing_optimizer
```

The default reads `data/breeders.json`. Copy the canonical roster from
`~/projects/wabbitry-receipt/data/breeders.json` when stock changes.

## Common Commands

```bash
scripts/check.sh   # ruff format + ruff check + mypy (static checks)
scripts/test.sh    # pytest
```

## ESL Compliance

This project follows the engineering standards in the shared
[eng-std-lib bundle](/home/hermes/projects/eslbundle/standards/AGENT-STANDARDS.md).

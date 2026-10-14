## Standards

This project follows the engineering standards in [/home/hermes/projects/eslbundle/standards/AGENT-STANDARDS.md](/home/hermes/projects/eslbundle/standards/AGENT-STANDARDS.md). AI consumers MUST load and follow it before doing work.

## Key norms

- **Python with ESL discipline** — ruff + mypy `--strict`, pydantic models, Google docstrings, `type-hints-on-public-signatures`, `command-wrapped-in-script` (`check.sh` / `test.sh`).
- **Conventional Commits** — issue references (`Closes #N` / `Refs #N`) on non-trivial commits; branch names `type/kebab-description`.
- **Pre-commit hooks** — gitleaks, trailing-whitespace, EOF fixer, large-file guard, merge-conflict check, conventional-commit message validation.
- **ADRs in `decisions/`** for architectural choices, dependency selections, and accepted trade-offs.
- **GitHub**: pushes use the LOBANZ PAT; one FG/account token per resource owner.

## Data source

The optimizer reads breeding stock from `data/breeders.json`. The canonical copy lives in the sibling `wabbitry-receipt` repo (`~/projects/wabbitry-receipt/data/breeders.json`); copy it here when the stock changes, or run against that path directly. Litters are not consumed by this tool (pairings are recomputed from the roster + parentage).

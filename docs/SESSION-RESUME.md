# Session Resume Handoff

Date: 2026-10-14 late (conversation ended ~local evening)
Author: Hermes
Purpose: Let the next session resume the wabbitry pairing optimizer work cleanly.

## TL;DR

Scaffolded a new ESL-compliant Python repo `wabbitry-pairing-optimizer` (on
GitHub, `Lobanz/wabbitry-pairing-optimizer`, empty-initialized this session).
Wrote the design doc (`docs/design.md`) capturing a multi-objective least-bad
breeding-pairing optimizer. Data (parentage) work was done in the sibling
`wabbitry-receipt` repo's `data/breeders.json`. Scaffolding and design are
DONE; **implementation has NOT started** (per operator's prerequisite: design
and impl plan before code). Next session: resolve 2 open design questions, write
the implementation plan, get operator 'go', then implement.

## Current Git / file state

### wabbitry-pairing-optimizer (new repo, `~/projects/wabbitry-pairing-optimizer`)
- Nothing committed yet (all files untracked). No commits on `main`.
- Scaffolded files:
  - `pyproject.toml` — ESL Python config (ruff, mypy --strict, pytest, pydantic)
  - `AGENT.md` — points AI at shared ESL: `/home/hermes/projects/eslbundle/standards/AGENT-STANDARDS.md` (lightweight ESL pattern, per operator)
  - `README.md`
  - `.pre-commit-config.yaml` — gitleaks, hygiene, conventional-pre-commit, ruff
  - `.gitignore`
  - `scripts/check.sh` + `scripts/test.sh` (executable)
  - `docs/design.md` — THE design (see below)
  - `src/wabbitry_pairing_optimizer/` — `__init__.py` (exports placeholder), `models.py`, `pairing.py`, `__main__.py` — all PLACEHOLDER/no logic; `models.py` still has the draft pydantic models from early scaffolding (Breeder, Pairing, PairingReport) but pairing.py/__main__.py were stripped to placeholders
  - `tests/`, `decisions/` — empty dirs
- NOTE: `models.py` may still contain earlier draft models; review for consistency with the design before implementing.

### wabbitry-receipt (`~/projects/wabbitry-receipt`) — DATA work done this session
- `data/breeders.json` — REWRITTEN to the new schema (28 rabbits, culled flag, parentage FKs). NOT yet committed — changes are on branch `cull-update-breeders` (earlier commit `c579bde` was the 20-rabbit-only version, now superseded by the 28-rabbit culled-flag version). **Branch state is messy** — needs a clean approach.
- Backup exists: `data/breeders.json.bak-20261014-011100` (the original 24-rabbit file).
- `data/litters.json` — NEW file from operator's `litters_2026-03-25.json` (12 litters, born 2026-03-25).
- Pre-existing untracked files (not ours): several `data/*_sale.json` files, `uv.lock` modified.

## The breed data (current, as entered into breeders.json)

Roster = 28 rabbits: 20 active + 8 culled (freezer, kept for pedigree).

Active — **Bucks (7):**
- M70: **Yaz** (founder/outcross, PRIORITY), **Zack** (= Zeek x Betsy), **Uno** (= Zeek x Abigail)
- TAMUK: **Willy** (founder), **Vader** (= Willy x Isabelle), **Xerces** (= Xander x Isabelle)
- Composite: **Vincent** (excluded from breeding — "diversity hire," does nothing)

Active — **Does (13):**
- M70 (7): **Abby, Amber** (= Zeek x Abigail, sisters), **Betty, Kiki, Lily, Maxine** (= Zeek x Betsy, sisters), **Opal** (uncertain parentage, marked `parentage_uncertain: true`, returned from a customer)
- TAMUK (6): **Isabelle** (founder), **Fiona** (= Ester x Willy), **Ginseng/Harmony** (founder sisters), **Iris/Jade** (= Xander x Harmony, sisters)

Culled (8): Zeek, Xander, Abigail, Betsy, Charlotte, Daisy, Ester, Florence (all founders, freezer).

Sibling pairs recorded: Abigail/Betsy (sisters), Charlotte/Daisy (sisters), Ginseng/Harmony (sisters).

## Genetic situation (the crux)

**M70 pool is a severe bottleneck.** Every M70 rabbit traces to founder buck
**Zeek** crossed over his two sister-does (Abigail, Betsy). Active M70 bucks
Zack and Uno are both Zeek-line. **Yaz is the ONLY M70 outcross** (founder,
unrelated). Opal's parentage is uncertain. M70s are nearly impossible to
source (source wabbitry closed), so **Yaz's replacement buck is the critical
diversity intervention** — his line must produce the buck that mediates the
bottleneck.

**TAMUK pool is healthier** — distinct lines (Willy x Isabelle -> Vader,
Xander x Isabelle -> Xerces, Xander x Harmony -> Iris/Jade) + founder outcrosses.

## Design decisions locked this session (see docs/design.md)

Constraints:
1. M70 x M70 only; TAMUK x TAMUK only (never cross)
2. Composite (Vincent) excluded
3. Culled rabbits excluded as candidates (kept as parents for pedigree)
4. All 13 active does must be assigned

Objectives:
1. Minimize inbreeding (least-related pairings) — PRIMARY
2. **Yaz sires 3 M70 litters** — strategic, highest-leverage (replacement buck)
3. Spread buck load (policy still open — Q3)

Tie-breaker (pairability): among equally least-bad pairings, choose the one
whose offspring pair best as kits next generation. Operator's counter-intuitive
finding: maximize first-gen genetic spread (buck to non-sisters) FRAGMENTS the
lines, leaving too few cross-pairable kits. Instead concentrate related kits
within a buck's output (half-sibs pair into trios best). Preserves diversity AND
improves pairability.

Yaz reliability: old, ~50% (or less) per-round success, poor aim ("aims too
high"), does not always receptive, conception not guaranteed. Reliability lever
saturated at 2-3 does (if can't get a litter off 3 does, 6 won't help — it's a
Yaz-side bottleneck). So 3 does, and the real question is WHICH 3.
The Yaz reliability/replacement model is a SEPARATE, REMOVABLE module (may reuse
shared infra, main optimizer must not depend on it) — "vestigial organ."

CLI: `python -m wabbitry_pairing_optimizer [breeders.json] [--output text|json]`
- dual output; `--output`, NOT `--format` (operator-confirmed convention);
- json for agents, text for humans.

Future-proofing: keep core logic decoupled from I/O (pure `roster -> PairingReport`
function; CLI/render are thin wrappers) for eventual roll-up with wabbitry-receipt.

Kinetic model: founder-ancestor sets; tiers outcross(0) > line-bred(1) >
siblings/parent-offspring(5, last resort only).

## Open questions for NEXT session (§9 of design)

1. **Data source:** copy breeders.json snapshot into this repo (self-contained for
   GitHub clones) vs read from wabbitry-receipt path? Not yet answered by operator.
2. **Buck load policy (Q3):** soft tie-break by load, or hard per-buck cap?
   Not answered. (Suggestion noted: soft given only 3 M70 bucks.)

## Where to resume / next steps

1. (Optional) Get the messy wabbitry-receipt git state cleaned — decide whether to
   commit the 28-rabbit culled-flag breeders.json + litters.json properly. The
   current branch `cull-update-breeders` has the superseded 20-rabbit commit.
2. Resolve the 2 open design questions (data source, buck load).
3. Write the **implementation plan** (files, functions, tests, scope) per
   operator's quasi-spec-driven workflow — that's the gate before ANY code.
4. Get explicit operator 'go', then implement.
5. Handle GitHub push with the correct PAT (LOBANZ for Lobanz/* repos; note the
   NARPNET PAT was active earlier — verify with `gh-use-pat.sh status` before push).

## Misc / context

- Operator's workflow: design -> impl plan -> explicit go -> staged implementation.
  "Read prompts literally." Nice-to-have: ESL python rules (see python.impl.md).
- Operator prefers `--output` (json/text) dual output, ESL discipline, decoupled
  future-proof code. "Code lives in the future."
- `my-cert-study` (Lobanz/my-cert-study) NOT reachable with either LOBANZ or NARPNET
  token — 403 not 404, exists elsewhere/different owner; separate thread, not
  blocking this work.
- Operator was driving (in a vehicle) during part of the session.

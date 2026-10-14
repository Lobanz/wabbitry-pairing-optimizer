# ADR 0002 — Rabbit names are canonical lowercase identifiers

Status: **Accepted** (2026-10-15)

## Context

Rabbit names serve as foreign keys throughout the data: `sire`, `dam`,
`siblings`, `founder_sisters`, `recipe` ancestor keys in `breeders.json`, and
`dam`/`sire` in the litter files. Rabbit data also carries `recipe` — a
precomputed ancestor-percentage map keyed by name. Names are also displayed in
receipts and the pairing report.

The question was whether to keep capitalized display names (e.g. "Abigail") as
the stored identity, or store lowercase and capitalize only on display.

## Decision

**Rabbit names are stored lowercase as the canonical identifier everywhere** —
in `name`, `sire`, `dam`, `siblings`, `founder_sisters`, `recipe` keys, and
litter `dam`/`sire` — applied identically across all data files. They are the
same everywhere: a name means one and only one rabbit, in one canonical form.

Display capitalization (proper nouns, e.g. "Abigail") is a **presentation
concern applied at render time**, not part of the stored identity. Lowercase also
produces cleaner lowercased identifiers/slugs (e.g. `yaz-betsy`).

## Motivation

- **Identifiers should be in their most programmatically-usable native form.**
  The data is consumed mostly by programs (optimizer, trio tool, receipts,
  agents), not read by people. Lowercase is the least surprising, most
  robust canonical form for keys and case-insensitive joins.
- **Consistency / avoid casing drift.** A single canonical form prevents the
  fragile situation where one file has "Opal" and another "opal" and joins break
  silently. Making it lowercase everywhere removes the ambiguity.
- **Display is a rendering concern**, so it stays out of the identity layer.

## Consequences

- All data files were rewritten to lowercase (`breeders.json`, and the 7
  `data/litters/*.json`) in **both** the pairing-optimizer repo (authoritative)
  and wabbitry-receipt (reference copy). Backups preserved in
  `/home/hermes/.hermes/cache/scratch/wabbitry-backup/`.
- Subsequently, the redundant `siblings` field was **removed** — sibling sets
  are derived from parentage (same `sire` AND `dam`); only `founder_sisters`
  (the non-computable founder case) is stored. The redundant root `litters.json`
  was also removed (per-round files in `data/litters/` are canonical).
- Sanity-checked after conversion: every FK reference resolves, no duplicate
  names, all `recipe` vectors still sum to 1.0.
- **wabbitry-receipt will now print lowercase names** unless/until it applies a
  display transformation (title-casing) at render. It "would need a couple
  tweaks" if capitalized display names are still wanted on receipts.
- Future code should **assume names are lowercase** and either consume them as
  lowercase or apply display capitalization only at the presentation boundary.

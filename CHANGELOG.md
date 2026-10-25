# Changelog

All notable changes to wabbitry-pairing-optimizer. Curated by hand; versions
are tagged `vMAJOR.MINOR.PATCH` (ESL `tags-follow-semver`).

## [0.2.0] — 2026-10-25

### Added

- Ad-hoc pair queries and ranked best-for-x: `--query 'sire:dam,...'` and
  `--rank buck:NAME|doe:NAME`, with `--sort`, `--limit`, `--all-strains` (#28).
- Bench breeders for a round: `--exclude 'zack, uno'` (#36).
- Doe-first pairings report table with Name + Breed columns (#26).
- Error-path hardening: unexpected CLI errors surface type + traceback (#27).
- Single-source package version (`__version__`, hatch path-read) — this release.

### Changed

- Breeding calendar alternates bucks: no buck breeds on two consecutive days
  (seeded multi-start search) (#29).
- `--pairs` accepts inline `sire:dam,...` specs and defaults to
  `data/fixed_pairs.json` (#28).
- Doe productivity detail (`ProductivityDetail`) exposed for queries; the
  index contract is unchanged (#28).

### Fixed

- `schedule_days` keyed on dam instead of sire — the round-length estimate
  undercounted (Oct round reported 4 days; correct estimate is 8) (#37).

## [0.1.0] — 2026-10-15

### Added

- Phase 0–6 foundation: roster/litter loading + validation, kinship (r),
  doe productivity index, two-tier scoring, multi-start assignment solver,
  dual-format report (JSON + Markdown) with two schedule calendars and CSVs,
  config-driven policy, path-traversal guards.
- Buck-diversity policy (`[diversity]` soft load penalty) (#23).
- Round snapshot promotion workflow (`data/YYYY-MM/`).

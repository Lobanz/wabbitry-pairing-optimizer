# ADR 0005 — Pairability metric: mixed-pair availability count (swappable)

Status: **Accepted** (2026-10-15)

## Context

Breeding is **intra-strain only** — M70 and TAMUK are never crossed. But
**selling** produces **mixed trios**: a buck from one strain + two (often
sister) does unrelated to him from the other strain. So the round's value is
partly *how sellable* its litters are. Pairability is the full-solution term
that scores this.

## Decision

Pairability is a full-solution score component, computed as an **availability
count**. Any cross-strain pair is automatically good (pools are never crossed,
so r ≈ 0), so pairability reduces to *how many such pairs the round's litters
support*.

Under a **uniform-litter assumption** (each pairing yields equal male/female,
same litter size), the count is deterministic from the pairings:
`pairability = min(M70 doe-kits, TAMUK buck-kits) + min(TAMUK doe-kits, M70 buck-kits)`.

This count is a **monotone proxy for mixed trios** (each trio = 2 does + 1 buck
from the opposite strain, so counting pairs ranks runs the same way). The real
trio optimizer runs **once** on the winning solution for an exact trio count —
but it is a **separate project**, not available on this repo.

**Pairability is a SWAPPABLE function** (`pairability(solution) -> float` in its
own module `pairability.py`), mode-selectable via config
(`[pairability] mode = "availability"`). If real-world trio-ability diverges from
the availability count, the function body can be replaced without touching the
solver or report.

## Motivation

- "any cross strain pair is good pair; it's just a matter of how many of them
  can we make" (operator) — so a faithful count (not a quality weighting) is the
  right metric; if it differs run-to-run, it's important.
- Making it a swappable seam honors the "decoupled core, thin wrappers"
  principle and the operator's "make it a function that can be altered later."

## Consequences

- `pairability.py` is a dedicated module in the dependency DAG.
- Availability-count is the shipped default; a fancier metric is a future,
  non-solver change.
- Uneven M70(7) vs TAMUK(6) litter counts cap the count on the smaller side —
  intended ("we can settle for max mixed pairs").

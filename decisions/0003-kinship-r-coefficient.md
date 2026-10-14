# ADR 0003 — Kinship model: coefficient of relationship (r) + configurable founder-sister factor

Status: **Accepted** (2026-10-15)

## Context

Pairings are ranked partly by how unrelated the buck and doe are. The data has
per-rabbit `recipe` fields (ancestor-percentage vectors summing to 1.0) and
`founder_sisters` records (founder does known to be siblings, e.g. abigail &
betsy — different rabbits, but they share the same parents).

Candidate approaches for "how related are two rabbits":
- a made-up 0–1 "genetic distance" with either 0=relate or 0=unrelated;
- founder-ancestor-set intersection (binary shared/not-shared);
- the standard **coefficient of relationship (r)**.

The founder-sister case is the crux: abigail and betsy have no recorded parents,
so a naive founder boundary says they are unrelated (r=0) — which is wrong. But
treating them as *identical* is also wrong ("they are different wabbits").

## Decision

Adopt **r, the coefficient of relationship**, as the standard kinship measure,
computed from each rabbit's `recipe`:

- **self / identical = 1.0**
- **full siblings & parent–offspring = 0.5** — the hard ceiling; no two
  distinct rabbits ever exceed 0.5 (the "different wabbit" guarantee is free).
- **unrelated (no shared ancestor) = 0.0**
- intermediate values per pedigree dilution.

r(A,B) = 2·f(A,B), where coancestry f(A,B) = ¼·(f(sA,sB)+f(sA,dB)+f(dA,sB)+
f(dA,dB)); f(A,A) = ½·(1+f(sA,dA)); founders with no parents are root boundaries.

**Configurable founder-sister factor S (default 0.5):** founder-sisters share
unknown-parent blood that r's founder boundary would count as 0. S credits that
blood universally across all *founder_sisters* pairs: two sister-founders are
treated as sharing fraction S, and cousins/bloodlines passing through them get
partial credit. S is a stated, operator-configurable value, not a hard fact.
S=0.5 treats sisters as full-sib-share.

## Motivation

- **It's the standard**, so wabbitry kinship speaks the same language as
  published rabbit genetics (inbreeding, breeding values).
- **"Different wabbit" is built in** — 0.5 is the natural cap for any two
  distinct rabbits; no extra clamp or special-casing needed.
- **It's already what the recipe computes** — r = correctly-normalized shared
  blood from the ancestor-percentage vectors; no new data required.
- **The one flaw (founder-sister = 0) is patched cleanly** by the single S knob
  applied universally, rather than per-pair hacks.

## Consequences

- Kinship tiering uses r-derived thresholds: outcross (r ≈ 0), line-bred
  (0 < r < ~0.5), full-sib/parent-offspring (r ≈ 0.5, heavy penalty, last resort).
- The score reported per pairing is r (0–0.5 range for distinct rabbits),
  complementing the coarse tier.
- S is a design constant held in config, applied to every founder-sister pair.
  Default 0.5; operator may change it and the values shift predictably.
- Verified against real data: betty×lily=0.5 (full sibs), betty×abby=0.25→0.375
  (cousins, depends on S), abigail×betsy=S, yaz×betty=0.0 (outcross), betty×betty=1.0.

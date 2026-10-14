# ADR 0001 — Yaz breeding strategy: Betsy-line only, to secure the replacement buck

Status: **Accepted** (2026-10-15)
Context: Fall 2026 M70 breeding round.

## Decision

For this breeding round, **Yaz sires 3 litters, all from the Betsy-line M70 does**:
**betty, lily, and kiki** (decided 2026-10-15). He does NOT breed across both M70
lines.

- **betty** — proven: threw an 8-kit litter (4M/4F) with Yaz in the 2026-03-25
  round; 3 litters on record.
- **lily** — proven: threw an 8-kit litter (4M/4F) with Zeek in the 2026-03-25
  round.
- **kiki** — chosen 3rd for her proven take-record: she kindled for Yaz in the
  2026-03-25 round (1-kit litter, small but she accepted). Selected over maxine
  because with an unreliable, "aims-too-high" sire like Yaz, a doe confirmed to
  accept is worth more than an untested doe (maxine has no own-litter record).

In the same round, **Zack and Uno cover the Abel-line does** (abby, amber), so the
Abel-line is still bred (by the Zeek-line bucks) and the cohort stays balanced.

## Motivation

Yaz is the ONLY non-Zeek (`outcross`) M70 blood in the operation, and must produce
the **buck that replaces him** — the diversity intervention for a Zeek-saturated
pool (M70s cannot be sourced; the source wabbitry closed).

Key facts established from the data / operator knowledge:
- The current M70 stock is 100% Zeek-line (daughters of founder does Abigail and
  Betsy, all sired by Zeek). There is no surviving Yaz-line.
- Yaz is a **poor sire but a genetic asset**: old, unreliable ("aims too high"),
  his own line (Charlotte & Daisy) gave small litters (~3 each) and none survived.
  But he is the only route to non-Zeek diversity.
- **Betsy is the more fertile/receptive founder than Abigail.** Fair comparison
  (give Abigail two 0-litters to match Betsy's 5-litter career) gives Abigail 3.80
  vs Betsy 5.60 average. This is not a sampling artifact — even a favorable
  correction keeps Betsy ahead.
- The current Betsy-line daughters (Betty, Lily) were the two biggest M70
  producers this round (8 kits each).

## Why "Betsy-line only" instead of spreading across both lines

1. **Determinacy / control.** With every Yaz doe being Zeek x Betsy, the
   replacement buck is **predetermined**: 50% Yaz outcross + 50% Betsy-line. We
   know exactly which line the offspring come from — no guesswork.
2. **No downside to buck-odds.** The probability of getting >=1 buck from Yaz
   depends on the number of does and their receptiveness, NOT on spreading across
   lines. Concentrating on the more receptive (Betsy) line does not lower the
   chance; if anything it raises it.
3. **Quality.** The replacement buck inherits the better (more fertile) line.

## Tradeoffs / consequences

- **Deprioritize trio-ability of Yaz's OWN litters this round** — they are not
  the primary sale product; the replacement buck is.
- **However:** because Yaz is on Betsy-line and Zack/Uno are on Abel-line, Yaz's
  kits (half-outcross) trio-ize cleanly with the Abel-line kits (maximally
  unrelated to Zeek-saturated Abel-line). So the strategy does NOT cost cohort
  trio-ability.
- **If Yaz's litters all take, they are the best least-bad pairings of the round**
  (most genetically distinct, most trio-able), serving double duty as replacement
  source AND high-value trios.

## Caveats / data limitations

- The Charlotte/Daisy small-litter result is **confounded**: they were sisters
  AND Yaz was the shared sire, so it could be the does, Yaz, or both. Current-round
  data (Yaz x Betty = 8, Yaz x Opal = 6 on strong Zeek-line does) shows Yaz can
  sire big litters on the right does. Do not over-count "poor sire."
- The replacement buck will likely be a modest producer — but it is the only path
  to non-Zeek diversity.

## The Yaz module is separate

The Yaz/replacement-buck reliability logic is a **separate, removable module** in
the optimizer: it may reuse shared infrastructure (breeder loading, ancestry) but
the main optimizer must not depend on it. Future rounds may revisit whether to
spread Yaz across lines as the pool changes.

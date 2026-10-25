# Design — Schedule alternation: no buck on consecutive days (issue #29)

Status: **design proposal for the reassessment gate — no implementation yet.**
Operator rules on the open decisions (§9) before any code. This feature
**revises a settled operator ruling** (see §2), so the operator explicitly
confirms before impl.

## 1. Problem

The calendar (`build_schedule`) packs a buck's breedings on **consecutive
days** — in the Oct round Zack breeds Days 3/4/5 (capped calendar) and
Days 1/2/3 (all-bucks). Meanwhile `schedule_days()` — the length estimate that
feeds the score — already assumes each buck's k does span `2k−1` days
(k breed + k−1 rest). The estimate assumes spacing the calendar never
delivers; the operator physically inserts the rest days.

Requirement: **bucks are bred every day where feasible, but no buck breeds on
two consecutive days.** The calendar should encode the alternation itself.

## 2. Current model (verified in code)

- `build_schedule`: a buck breeds ≤1 doe/day; ≤`max_bucks_per_day` distinct
  bucks/day (0 = unlimited); **no rest-day constraint**; deterministic
  sorted-buck greedy; days exist only when breedings occur.
- `schedule_days`: per-buck span `2k−1`, batched by `buck_batch_capacity`
  (batch span = max), round = sum of batch spans. Already prices rest days.
- Earlier operator ruling (schedule ADR): *no rest days in the model — "I will
  insert the rest day."* **This design reverses that ruling for the calendar
  render; the length estimate already assumed the spacing.**

## 3. Requirements

- **R1 (hard):** a buck never breeds on two consecutive calendar days.
- **R2 (soft):** every day has ≥1 breeding where feasible — minimize idle days.
- **R3:** applies to BOTH calendars (capped at N bucks/day + all-bucks/day).
- **R4:** deterministic (seeded), like the rest of the tool.
- **R5:** `schedule_days` estimate unchanged (verify — per-buck `2k−1` still
  holds under alternation inside a batch).

## 4. Feasibility

A feasible schedule always exists: buck j breeds k_j does on days
1,3,5,…,2k_j−1 → makespan `max(2k_j−1)`. No unbred failure mode.

Idle days are **unavoidable** when the "no-consecutive" constraint and the
buck load leave gaps no other buck can fill (e.g. a single buck on 3 does →
Days 1,3,5, idle 2 and 4). R2 is best-effort: minimize, never assert zero.

## 5. Algorithm options

**Option A — greedy + eligibility filter.** Each day, breed eligible bucks
(has does left AND did not breed yesterday), sorted, cap applied. Minimal
change; can leave avoidable idle days (2-buck example: A=3 does, B=1 doe →
greedy breeds A+B Day 1, nobody eligible Day 2 → 2 idle days; staggering
B→Day 2 gives 1 idle).

**Option B — greedy with remaining-count priority (recommended).** At each
day, among eligible bucks prefer those with the **most does remaining**; they
must span the most days, so breeding them early fills gaps for later.
Cheap, deterministic, and on the real roster (8 bucks, max load 4) should keep
idle days near the theoretical floor. Verify empirically before choosing.

**Option C — small multi-start scheduling search.** Like the solver: seeded
runs assign breedings to the earliest feasible day; score by (makespan, idle
days); keep the best. Most robust idle minimization; most code for a render
concern.

**Recommend B**, with C as the escalation if B leaves avoidable idle days on
the real roster.

## 6. Rendering / reporting

- With alternation the calendar days are **spaced** (Day 1, Day 3, Day 5) —
  the gap **is** the rest day, self-evident from the Day numbers. No new
  rendering needed beyond the spaced numbering.
- Keep the calendar dense (only breeding days listed) — recommended — or show
  explicit `(rest)` rows. Decision point.
- JSON schedule keys follow the spaced Day numbers automatically.

## 7. Interaction with assignment / diversity

Alternation does not change assignment (does→bucks) — out of scope. A
concentrated buck load (one buck on 4 does) forces idle gaps elsewhere
(`2k−1 = 7` span). Re-balancing loads to reduce forced idle days is a
**follow-on decision**, already flagged out of scope in #29.

## 8. Tests (tests/test_schedule.py)

- Property: no buck on two consecutive days (real roster + synthetic sets).
- Single-buck feasibility: spaced days, correct makespan.
- Idle-day sanity: multi-buck interleave fills gaps (Option B behavior).
- Determinism with seed; capped + unlimited both honored.
- `schedule_days` anchors unchanged (existing tests stay green).

## 9. Open decisions (operator)

- [ ] **Confirm the calendar should now encode rest-day spacing** (R1 revises
      the earlier "I will insert the rest day" ruling)
- [ ] Algorithm: **B (recommended)** vs A vs C
- [ ] Idle-day display: dense (recommended) vs explicit `(rest)` rows
- [ ] `schedule_days` estimate unchanged (recommended) — confirm
- [ ] Follow-on: re-balance buck loads to cut forced idle days (defer)

## 10. Out of scope

- Assignment / kinship / scoring changes; fixed-pair logic; report content
  beyond the schedule tables + JSON schedule keys.

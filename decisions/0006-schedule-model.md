# ADR 0006 — Breeding calendar / schedule model

Status: **Accepted** (2026-10-15)

## Context

The round takes the operator time to execute — trips out to the wabbitry each
morning and evening. The schedule-length factor of the full-solution score
reflects how long a pairing plan takes to run.

## Decision

- **One breeding = AM + PM on the same day**: each doe gets two sessions with
  the buck on one breeding day to confirm take. These are **two parts of one
  breeding**, not two breedings. (The real schedule units are calendar days.)
- **A doe is bred by exactly one buck** (one litter per doe per round); a buck
  may breed **multiple does** (buck load allowed).
- A buck servicing `k` does spans **`2k−1` days** (each doe one breeding day,
  one day rest between).
- The operator can watch **≤ buck_batch_capacity bucks** concurrently (default
  4); round length = **sum over ≤4-buck batches of the max buck span**.
- Schedule length is operator labor, not buck physiology — it's scored with a
  configurable negative weight (`weight_schedule_length`, default −0.3).

## Motivation

- The operator trips AM+PM daily, so each breeding day is "one calendar day"
  of their logistics.
- Batching reflects that they can run several bucks in parallel, so the round
  is bounded by the slowest buck per batch, summed across batches.

## Consequences

- `buck_batch_capacity` and `weight_schedule_length` are config knobs.
- The schedule is a scored, minimized factor in the full-solution score — not
  a hard constraint.

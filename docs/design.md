# Design — Wabbitry Pairing Optimizer

Status: **Design decisions resolved (2026-10-15).** All open questions in §10
are closed; kinship uses the r-coefficient + founder-sister factor (ADR 0003);
the Yaz strategy is locked to betty/lily/kiki (ADR 0001); names are lowercase
(ADR 0002); scoring uses two tiers with all policy knobs in a TOML config;
assignment is fixed-pairs + multi-start ranked greedy. **Next gate: the
implementation plan must be reviewed and an explicit operator 'go' received
before any code is written.** Module layout is one-concern-per-file with a
dependency DAG (see §11).

## 1. Problem

Wascally Wabbitry needs to breed a set of does this fall round and must choose,
for each doe, which buck to breed her to. The choice is constrained by genetics:
M70 and TAMUK NZW lines have been kept separate for generations to preserve
hybrid vigor for mixed-sales customers, and M70 stock is now nearly impossible
to source — making the M70 pool a genetic bottleneck.

This tool produces the **least-bad** set of pairings: it respects the hard
constraints and minimizes inbreeding within each pool, rather than chasing an
unreachable ideal.

### Scope

- **In scope:** read breeding stock + parentage; score buck x doe kinship;
  assign every doe a buck; report the pairings.
- **Out of scope (separate tools/projects):** triplet-from-litters grouping
  (the existing "magic program"), sale receipt generation (wabbitry-receipt),
  and a from-scratch rewrite of the trio optimizer (future project).

## 2. Data model

Source of truth: `breeders.json` (canonical copy lives in this repo's `data/`
dir; the sibling `wabbitry-receipt` repo holds a reference copy). One object per
rabbit:

**Name casing (decided 2026-10-15):** rabbit names are stored **lowercase** as
canonical identifiers — the same everywhere (`name`, `sire`, `dam`,
`founder_sisters`, `recipe` keys, and litter `dam`/`sire`). Identifiers live in
their most programmatically-usable native form; display capitalization (proper
nouns) is applied at render time when necessary. wabbitry-receipt may need
display tweaks to title-case names it prints.

```json
{
  "name": "abigail",
  "breed": "M70 NZW",
  "gender": "F",
  "culled": true,
  "founder": true,
  "sire": null,
  "dam": null,
  "parentage_uncertain": false,
  "founder_sisters": ["betsy"],
  "recipe": { "abigail": 1.0 }
}
```

Litter history lives in `data/litters/*.json` — one file per breeding round
(7 rounds on file), each a list of `{dam, sire, born, males, females}`. Used to
estimate per-doe and mother-line reliability, and to plan trio-ability.

Field semantics:

- `breed` — combined strain + breed. Strain is the first token: `M70`, `TAMUK`,
  or `Composite`. `Composite` is excluded from breeding.
- `gender` — `M` (buck) / `F` (doe).
- `culled` — removed from the active pool (e.g. freezer) but kept as a valid
  parent reference. Excluded as a breeding candidate.
- `founder` — parentage unknown/irrelevant; treated as an unrelated founder
  whose identity terminates ancestry walks.
- `sire` / `dam` — parent FK (name). `None` when unknown. A parent may be a
  culled rabbit (freezer) — that is valid; the pedigree reference persists.
- `parentage_uncertain` — `sire`/`dam` are a best guess, not confirmed (e.g.
  Opal, returned from a customer). Treated as a founder boundary when walking
  ancestry — we do not over-trust guesses.
- `founder_sisters` — list of founder does known to be siblings (e.g. abigail
  and betsy). This is the **only** sibling relationship that cannot be computed
  from parentage (founders have no recorded parents). Used to merge founder-
  sister blood when computing ancestry, so that two founders who are sisters are
  not counted as fully unrelated (this is the correction behind the
  Betsy-vs-Abigail fertility analysis).
  - **There is NO stored `siblings` field.** For rabbits with parentage, a
    full-sibling set is **derived** from parentage: **Full-sibling ⟺ same
    `sire` AND same `dam`.** Group rabbits by the `(sire, dam)` pair to get
    sibling sets. `founder_sisters` is kept as the sole exception for founders
    (no parentage to compute from).
- `recipe` — precomputed ancestor-percentage vector for each breeder, summing to
  1.0. A map `{ancestor_name: contribution}` covering **every known ancestor**
  (NOT just founders, and NOT founder-sister-collapsed — keeping distinct
  ancestors, including both Abigail and Betsy separately, preserves information).
  Founders are like self-signed root CAs: a founder with no recorded parents has
  recipe `{Name: 1.0}` (they are the trust root that terminates the chain). A
  child's recipe = half of each parent's recipe, summed. Computed **one-time** and
  stored statically in breeders.json (rabbits don't change between rounds) so
  consumers (optimizer, trio tool, receipts) read the vector directly instead of
  recursing the pedigree on every use. The founder-sister correction is applied
  by consumers on top of the raw recipe when needed.

### Model (pydantic)

`Breeder` with the fields above (plus `founder_sisters`); `Pairing
{sire, dam, kinship, penalty}`; `PairingReport {pairings, unbred_does,
total_penalty}`.

## 3. Hard constraints

1. **M70 x M70 only; TAMUK x TAMUK only.** Never cross pools.
2. **Composite strain excluded** (e.g. Vincent).
3. **Culled rabbits excluded** as candidates (kept as parents only).
4. **All active does must be assigned** (7 M70 + 6 TAMUK), unless genuinely
   unavoidable. Pre-decided **fixed pairs** are treated as already-assigned (and
   both sides excluded from the automated pools); any doe left with no buck is
   an order-trap artifact penalized in the full-solution score, and a sibling
   pairing is forced only as a last resort rather than leaving a doe unbred.

## 4. Objectives

1. **Minimize inbreeding** within each pool.
2. **Yaz sires 3 M70 litters — strategic priority, Betsy-line only.**
   Yaz is the ONLY non-Zeek M70 blood and must produce the **buck that replaces
   him** as the diversity intervention for a Zeek-saturated pool (source wabbitry
   closed; no other source).
   - **Yaz is a POOR sire but a genetic asset.** His own line (via founding does
     Charlotte & Daisy) gave small litters (~3 each) and he has NO surviving
     offspring (earlier ones sold). He is old, unreliable, "aims too high." The
     replacement buck will be a modest producer, but it is the only path to
     non-Zeek diversity.
     - **Caveat (confounded):** the Charlotte/Daisy small-litter result is
       ambiguous (they were sisters AND Yaz was the common sire). Current-round
       data (Yaz x Betty = 8, Yaz x Opal = 6 on strong Zeek-line does) shows Yaz
       can sire big litters on the right does. Do not over-count "poor sire."
   - **THE DECISION: Yaz displaces Zeek on the Betsy-line this breeding.** All 3
     of Yaz's does come from the **Betsy-line** — **betty, lily, kiki**
     (decided 2026-10-15) — NOT spread across both lines.
     - **Why these 3:** betty threw an 8-kit litter with Yaz last round (proven);
       lily threw an 8-kit litter with Zeek (proven); kiki was chosen as the 3rd
       for her proven take-record (she kindled for Yaz last round), over maxine
       (no own-litter record, untested).
     - **Determinacy / control:** with every Yaz doe being Zeek x Betsy, the
       replacement buck is **predetermined** — 50% Yaz outcross + 50% Betsy-line.
       We know exactly what line the offspring come from; no guesswork. We
       control quality by using the more fertile/receptive line.
     - **Why Betsy-line (not Abel-line):** fair-comparison correction (giving
       Abigail two 0-litters to match Betsy's 5-litter career) shows **Betsy is
       the more fertile/receptive founder** (3.80 vs 5.60 corrected) and the
       current Betsy-line daughters (Betty, Lily) are the two biggest M70
       producers this round (8 kits each). Spreading across lines does NOT raise
       the odds of getting >=1 buck from Yaz (buck-odds depend on number of does
       and their receptiveness, not on line spread), so concentrate on the best
       line.
     - **Trio-ability of the replacement (not the litters):** this round we
       deprioritize trio-ability of Yaz's OWN litters — they are not the sale
       product. What matters is quality AND trio-ability of the REPLACEMENT buck.
       Because Yaz is on the Betsy-line and Zack/Uno cover the Abel-line does,
       Yaz's kits (half-Yaz outcross) **trio-ize cleanly with the Abel-line kits**
       (maximally unrelated to Zeek-saturated Abel-line) — so control over the
       replacement does NOT cost cohort trio-ability.
     - **But if Yaz's litters DO take, they are the best least-bad pairings of
       the round.** Since every Yaz kit is 50% outcross + 50% Betsy-line and the
       rest of the cohort is Abel-line, Yaz's kits are the most genetically
       distinct and most trio-able of the entire breeding. So Yaz's litters serve
       double duty: replacement-buck source AND potentially the highest-value,
       best-pairable trios. We simply cannot COUNT on them (Yaz's unreliability),
       so we hedge by not depending on them — but if they land, they are gold.
   - **Why 3 does:** reliability lever saturated at 2-3 does (Yaz-side
     bottleneck). 3 Betsy-line does maximize the chance at least one takes.
   - The Yaz/replacement-buck reliability model is a **separate, removable
     module**: it may reuse shared infrastructure (breeder loading, ancestry)
     but the main optimizer must not depend on it.
3. **Spread buck load** — governed by trio-ability of the offspring, not an
   arbitrary cap. (Resolved 2026-10-15; see Pairability tie-breaker below.)

### Pairability as a full-solution term (2026-10-15)

**A trio (sellable breeding unit) = 1 buck + 2 does (often sisters) not related
to the buck.** A **MIXED trio** is the same but **cross-strain**: the buck from
one strain, the 2 sister-does from the other (e.g. M70 buck + 2 TAMUK sisters,
or vice versa). Breeding is strictly intra-strain, but **selling** packages the
round's litters into **mixed trios** — the preferred sale unit (outcross combo).
The existing trio optimizer does exactly this: it **maximizes the number of
mixed trios**, preferring mixed and falling back to mixed pairs.

A run solution's **pairability** = how many such (mixed) trios its assumed
litters support. Because the trio optimizer is applied to the round's *resulting
kits*, pairability reflects the round's pairing choices: whether the run's
pairings yield enough buck-kits on one strain and unrelated sister-doe-pairs on
the other to form mixed trios. **Different solutions differ in this count.**

**Computed in the run score as a cheap PAIR proxy** (not the full trio
optimizer per run): a **mixed pair = 1 doe from one strain's litter + 1 buck
from the other strain's litter** (cross-strain, automatically unrelated — pool
separation gives r≈0). The full-solution pairability term = the number/quality
of such mixed pairs the run's assumed uniform litters support, judged by a
recipe/r comparison between each doe and buck. The pair is the building block
the trio optimizer extends into a full mixed trio (buck + 2 does), so ranking
on pairs ranks on trios (monotone proxy). Optionally, the **real trio optimizer
runs once** on the single winning solution for the exact trio count in the
human report — not per candidate.

**Pairability is a SWAPPABLE function, not a hardcoded formula.** It lives in
its own module (`pairability.py`) with a clean interface
`pairability(solution) -> float`. The current implementation is the cheap
**mixed-pair availability count** (under the uniform 50/50 litter assumption):
`min(M70 doe-kits, TAMUK buck-kits) + min(TAMUK doe-kits, M70 buck-kits)`.
If field use shows that count doesn't faithfully reflect real trio-ability, the
**body is swapped** (e.g. a recipe-quality-weighted variant, or a measure backed
by the exact trio optimizer) with **no change to the solver or report** — the
solver calls the same `pairability()` seam, and the config may select the mode.

Uniform-litter assumption with equal 50/50 sexes (forward-looking: actual
litter outcomes unknowable at planning time) makes the pair/trio count
deterministic from the pairings alone.

The two-pass objective:
1. **Primary:** minimize kinship (least-related pairings).
2. **Full-solution:** maximize offspring **pairability** (mixed-trio count via
   the cheap mixed-pair proxy), driving run selection.

## 5. Kinship model

**Coefficient of relationship (r)** — the standard genetics measure, computed from
each rabbit's `recipe` (ancestor-percentage vector):

- **self / identical = 1.0**
- **full siblings & parent–offspring = 0.5** — the hard ceiling; **no two distinct
  rabbits ever exceed 0.5** (this answers the "it's a different wabbit" problem:
  identical recipes never mean identical rabbits).
- **half-sibs / first cousins etc. < 0.5** per the pedigree dilution.
- **unrelated (no shared ancestor) = 0.0**

Computation: r(A,B) = 2·f(A,B), where the coancestry f(A,B) = ¼·(f(sA,sB)+f(sA,dB)
+f(dA,sB)+f(dA,dB)) over the four grandparental cross-terms; f(A,A) = ½·(1+f(sA,dA));
founders with no parents are root boundaries (f=0 except self). Equivalently derived
from recipes as the correctly-normalized shared-blood fraction.

**Configurable founder-sister factor S (default 0.5):** founders recorded as
sisters (`founder_sisters`, e.g. abigail & betsy) share an *unknown-parent* blood
that r's founder boundary would otherwise count as 0. The S knob credits that
blood **universally across all founder-sister pairs**: two sister-founders are
treated as sharing fraction S (so abigail×betsy = S, and cousins through them get
partial credit). S=0.5 (default) treats sisters as full-sib-share; it is a stated,
operator-configurable opinion, not a hard fact. This is how the "different wabbit,
but they share the same parents" problem is handled.

Pairings are classified into tiers (best to worst), using the r-derived kinship.
Each tier carries a **configurable penalty** (`[scoring.tier_penalty]`,
`data/config.toml`), not a magic constant:

| Tier | Meaning | Penalty (config) |
|------|---------|---------|
| Outcross | r ≤ `outcross_r_max` (default ~0.1) | `penalty_outcross` (0) |
| Line-bred | above outcross, below ~0.5 | `penalty_line_bred` (1) |
| Siblings / parent-offspring | r at/near 0.5 | `penalty_sibling` (5) |

Siblings carry the heaviest penalty and are used **only** as a last resort to cover
an otherwise-unbred doe (operator: "kinda bad but might be unavoidable").

### Rationale for r over founder-set intersection

The litters are recorded flat (dam/sire/m/f counts), so per-kit lineage is
under-specified. Full Wright's F requires deeper pedigrees than we track.
**r computed from the recipe ancestor-percentage vectors** is the appropriate,
data-available proxy: it collapses cleanly to the standard anchor values
(full-sib 0.5, unrelated 0.0) without needing per-kit ancestry, and the
configurable founder-sister factor S patches the one place the flat data is
wrong (sister-founders share unknown-parent blood). This gives a continuous,
universal, biologically-standard kinship measure rather than a binary
"shared/not-shared" founder test.

## 6. Assignment algorithm

Per strain pool (M70, TAMUK), independent:

1. Compute kinship (r) tables and coarse tiers for all active buck/doe pairs
   (see §5), plus the doe productivity index for each active doe (see §8).
2. **Fixed-pairings pass:** load the pre-decided pairings from the `--pairs`
   input (a list of `Pairing` objects, same schema as output — e.g.
   `yaz=betty`, `yaz=lily`, `yaz=kiki`). For each fixed pair:
   - **compute its FULL rationale scores** (`r`, `doe_history`, tier,
     `kinship_penalty`) — identical to an auto pair, so the report is uniform
     and the fixed choices are auditable ("so we know") even though not chosen
     by the optimizer; set `pair_type = "fixed"` (vs `auto` / `last_resort`).
   - **exclude both sides** from the automated assignment pools (so those does
     aren't double-assigned, and those bucks aren't auto-assigned elsewhere)
   - keep them **in the model** (not deleted) so kinship/trio-ability reasoning
     can still see them
   - include them in the final output report alongside the auto-assigned pairs.
   This is how the Yaz pass (ADR 0001: yaz x betty/lily/kiki) is expressed, and
   how any future pre-decided pairings work.
3. **Ranked multi-start pass (per operator's trio-optimizer finding that
   processing order materially changes the result):**
   - **Shuffle ALL pools each run** — the remaining does AND remaining bucks (and
     any other pool being drawn from). Ties in the per-pairing score resolve to
     whichever candidate comes first in the shuffled order, so shuffling every
     pool, not just does, avoids a hidden buck-side bias.
   - For each run: iterate the shuffled does, assign each the highest-scoring
     buck per the per-pairing score (r + doe_history); record the resulting
     complete solution and its **full-solution score** (§8 tier 2).
   - **Stall-based termination** (operator-observed that solutions converge fast
     with an occasional late better one): run solution objects carry a
     **comparison function**, so a new best (winner) is known immediately as runs
     complete. Terminate only **after MIN_RUNS runs** AND **when no new winner has
     appeared in STALL_LIMIT runs** (e.g. MIN_RUNS=500, STALL_LIMIT=100). The
     min-runs gate guarantees enough exploration before any early stop can fire,
     avoiding the degenerate case of shutting down almost immediately if the first
     runs are lucky; after min-runs, the stall gate auto-adapts (fast when
     converged, still escapes local optima via the occasional late winner).
   - Keep the single best solution (the current winner).
4. **Doe production history** is the primary tiebreaker when r ties: rank does
   by their own (or mother's, where own is thin) litter history via the doe
   productivity index (size + consistency, outliers trimmed, blended with
   mother by evidence) — see §8. (Fixed pairs like the Yaz decision already
   encode this choice.)
5. Sibling-tier matches are allowed only when no lower-tier buck is available
   for that doe (operator-approved last resort).

## 7. Output

A human-readable pairing report: each `doe <- buck [kinship]`, plus a list of
any unbred does and the total penalty. A `PairingReport` pydantic object carries
the structured result so it can later feed the trio/receipt flow if desired.

## 8. CLI

`python -m wabbitry_pairing_optimizer [breeders.json] [--pairs <file>]
[--config <file>] [--output json|text] [--output-dir <dir>]` — loads and
validates the roster, applies any pre-decided fixed pairings, runs the
optimizer, emits the report. Default path `data/breeders.json`; no pairs by
default; default CLI output `json`.

**Two separate layers (2026-10-15):**

1. **`--output json|text` governs ALL program emissions** over the terminal —
   help, version info, errors, every message — so that an agent or program
   driving this CLI can consume *everything* it emits structurally when asked
   (`json`) instead of scraping human text. This matches the operator's other
   CLIs. `text` is the human-readable emission mode. This is about the
   **program ↔ terminal/agent interface**, not the result content.

2. **The pairing RESULT itself is always emitted in BOTH json and markdown** —
   one structured, one a human-readable report — independently of the `--output`
   choice. The json carries the structured pairing data (incl. the kinship and
   doe-productivity tables); the markdown is the comprehensive human report
   rendering that same data. Both are always produced; which goes to stdout vs
   to the output-dir is the rendering detail.

The two layers are independent: `--output` selects the program's emission
language; the result content is dual-format by design.

- `--pairs <file>` — optional path to a JSON file of **pre-decided pairings**,
  a list of `Pairing` objects matching the output schema, e.g.
  `[{"sire":"yaz","dam":"betty"}, ...]`. Each fixed pair is removed from the
  automated assignment (both sides excluded from the running pools) but kept in
  the model and **included in the output report**. This is how the decided Yaz
  pairings (and any others) are supplied.
- `--config <file>` — path to a **TOML config** carrying the operator-policy
  knobs (see Config section). Default `data/config.toml`.
- `--output-dir <dir>` — the single destination directory **everything written
  out lands in** (default from `[output]` config, e.g. `out/`). The dual-format
  result + table artifacts all go here:
  - `<outdir>/wabbitry-report.json` — structured result (pairings + rationale
    scores, full-solution score breakdown) incl. the kinship and doe-productivity
    tables as data. For agents/software.
  - `<outdir>/wabbitry-report.md` — the comprehensive human markdown report:
    pairings + per-pairing scores, solution-score components, the **kinship
    table** and **doe-productivity table** rendered inline. The audit-trail
    deliverable.
  - `<outdir>/kinship-table.csv` — r matrix as standalone data
  - `<outdir>/doe-productivity.csv` — doe index / own-vs-mother as standalone data
  (Filenames are configurable in `[output]`, not magic.) Terminal stdout is for
  program emissions per `--output json|text`; the result artifacts are files in
  the output-dir.
- `--min-runs N`, `--stall N` — optimization run control (see §6 step 3;
  defaults e.g. MIN_RUNS=500, STALL_LIMIT=100).

**Kit recipe (expected offspring parentage) is a render-time derivation, not a
stored pairing field.** The `Pairing` decision record stays
`{sire, dam, kinship, penalty}`. A kit's expected recipe is computed on demand:
`kit_recipe = 0.5 * sire.recipe + 0.5 * dam.recipe` (each an ancestor-percentage
vector, summing to 1.0). A *recipe report* — full offspring parentage per
pairing (e.g. `yaz:50, zeek:25, betsy:25`) — is a **separate presentation
animal** that can be generated from the pairing decisions at render time, not a
change to the decision schema.

**Rationale scores (2026-10-15):** bare `{sire, dam, kinship, penalty}` loses
*why* a pairing was chosen, which matters for a consequential decision. Each
pairing therefore carries a **scores object** — an array/map of component
signals plus a final weighted composite, so the rationale is auditable rather
than a black box:

- `r` — coefficient of relationship (0.0 unrelated … 0.5 full-sib for distinct
  rabbits; see §5), the continuous kinship measure complementing the coarse tier.
- `doe_history` — the doe's production/reliability signal (e.g. litter count,
  avg/peak size, rounds) where the data is available.
- `kinship_penalty` — the tier penalty (outcross=0 / line-bred=1 / sibling=5).
- `pair_type` — `fixed` (pre-decided, e.g. Yaz), `auto` (greedy assignment), or
  `last_resort` (forced sibling).
- `weighted` — the final composite score, with the weight choices documented as
  a stated policy (an opinion, not absolute truth).

Keeping the component scores alongside the composite avoids the trap of a single
opaque number hiding the weight choices.

**Two scoring tiers (2026-10-15):**
1. **Per-pairing score** — picks a buck for *one* doe: `r` + `doe_history`
   (breaks ties between candidate bucks for a single doe).
2. **Full-solution score** — ranks *complete* assignment sets (from the
   multi-start runs, §6 step 3). Weighted components:
   - **1. sum of r** across all pairings (minimize overall inbreeding)
   - **2. sum of doe production history** (reward breeding productive does)
   - **3. unbred-doe penalty** — a doe accidentally left with no buck (order
     trap), the discriminator between orders; NOT the same as a doe's sparse
     own record (e.g. maxine n=1). Any solution leaving a doe unbred is
     strongly penalized.
   - **4. sibling last-resort penalty** — penalize any forced full-sib /
     parent-offspring pairing, so solutions that avoided incest rank higher.
   - **5. schedule length** — the calendar span of the round, driven by the
     operator's daily breeding trips: each doe takes one breeding day (the
     operator goes out **early AM and PM**), and **waits a full day between**
     breeding days, so a buck servicing k does spans ~2k−1 days (k breeding days
     + k−1 rest days). The operator manages about **4 bucks at a time**, so bucks
     are bred in batching of ≤4; a batch's span = max over its bucks of (2·does−1),
     and the round length = **sum over batches of (batch span)** (you can't start
     the next batch until the current one's longest buck is done). The optimizer
     computes the day count and the batched schedule. Spreading does across bucks
     and balancing loads shortens the round and saves the operator trips; the
     weight reflects operator labor — higher than a pure tiebreaker but secondary
     to breeding quality.
   - **6. pairability (mixed-pair proxy)** — how many mixed trios the round's
     assumed litters support, scored cheaply on **mixed pairs**: a mixed pair =
     **1 doe from one strain's litter + 1 buck from the other strain's litter**
     (cross-strain, so automatically unrelated — pool separation, r≈0). The
     pairability signal = the **number/quality of such mixed pairs** the run's
     assumed uniform 50/50 litters support, judged by a **recipe/r comparison**
     between each doe and buck. This is the building block the trio optimizer
     extends into full mixed trios; ranking on pairs ranks on trios (monotone
     proxy). See §4. The real trio optimizer may run once on the winner for an
     exact trio count.
   The weights for both tiers are a **stated, operator-policy choice** (an
   opinion, not a hard fact) and are carried in the output so the ranking is
   auditable.

## 9. Config (operator-policy knobs)

All tunable, opinion values live in a **TOML config file** (default
`data/config.toml`) so every policy choice is visible, tweakable, and auditable
in one place rather than scattered as constants. Structure:

```toml
[kinship]
sister_factor = 0.5          # founder-sister shared blood (S), ADR 0003
outcross_r_max = 0.1         # r below this = outcross tier (config, not magic)

[productivity]
size_weight = 0.6            # avg litter size vs consistency
consistency_weight = 0.4
evidence_K = 2.0             # own-vs-mother blend smoothing (own_count/(own_count+K))
outlier_trim = true          # drop freak big/small litters before averaging
outlier_method = "iqr"       # how outliers detected ("iqr"/"zscore"/"none")
outlier_threshold = 1.5      # e.g. 1.5*IQR or z-score bound

[scoring.per_pairing]
weight_r = 1.0               # r vs doe_history in per-pairing pick
weight_doe_history = 1.0

[scoring.tier_penalty]
penalty_outcross = 0         # kinship tier penalties (config, not magic)
penalty_line_bred = 1
penalty_sibling = 5

[scoring.full_solution]
weight_sum_r = 1.0
weight_sum_history = 1.0
weight_unbred = -5.0         # strong penalty per unbred doe
weight_sibling = -3.0        # penalty per forced sibling/parent-offspring
weight_schedule_length = -0.3  # minimize round calendar span (operator labor)
weight_pairability = 1.0       # maximize pairability (mixed-pair proxy for trios)

[pairability]
mode = "availability"        # swappable metric: mixed-pair count (see §4); body/impl replaceable later

[optimization]
min_runs = 500               # minimum runs before stall-termination can fire
stall_limit = 100            # stop after this many runs with no new winner
seed = 0                     # fixed seed for reproducibility (0 = random/unset)
buck_batch_capacity = 4      # concurrent bucks operated at once (batching)

[output]
output_dir = "out"           # default destination dir for result artifacts
report_json = "wabbitry-report.json"
report_md = "wabbitry-report.md"
kinship_table_csv = "kinship-table.csv"
doe_productivity_csv = "doe-productivity.csv"
```

Weights are a **stated operator policy** (an opinion, not a fact) and are
reflected in the output so the ranking is auditable. Changing a weight shifts
the result predictably; the config is the single place to tweak.

## 10. Open questions (resolve before impl plan)

1. Data source: this repo is the **natural home** for breeders.json (and
   litters.json). In wabbitry-receipt they were only a *reference* for building
   sale JSON. The authoritative `breeders.json` / `litters.json` live here and
   are consumed by the optimizer; wabbitry-receipt can reference/copy from this
   repo. (Resolved 2026-10-15.)
2. Yaz's 3 does: resolved — betty, lily, kiki (all Betsy-line) to secure the
   replacement buck (see ADR 0001 and §4 objective 2). (Resolved 2026-10-15.)
3. Spread buck load: subsumed by the trio-ability/pairability objective — not
   a separate policy. (Resolved 2026-10-15.)
4. Unbred tolerance: if a doe has no non-sibling buck, leave her unbred or force
   a sibling pairing? (Operator already answered: force as last resort.)

## 11. Future-proofing / roll-up

This tool and `wabbitry-receipt` will likely be consolidated into a larger
system eventually. Two consequences:

1. **Keep the core logic decoupled from I/O.** The optimizer is a pure function
   (`roster, fixed_pairs, config -> Solution`); the CLI and the text/json/md
   rendering are thin wrappers around it. This mirrors wabbitry-receipt's
   models/renderer split and makes the pairing logic importable and reusable
   inside a larger system later.
2. **Agent-readable output is a deliberate affordance.** The json output and ESL
   discipline are patterns to carry forward, not overhead for this one tool.
   Small-project discipline is what lets modules roll up cleanly later.

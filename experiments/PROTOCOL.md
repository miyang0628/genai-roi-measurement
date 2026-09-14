# Three-Tier Robustness Experiment — Protocol

Purpose: strengthen the paper's empirical basis (reviewer point M3) by reporting
the five-axis validation metrics across three model tiers instead of a single
weak-tier run, with repeated runs so that reliability is measured rather than
asserted.

## Design (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Pipeline scope | **Full pipeline** (Agent 1 → 1.5 process graph → Agent 2 → Agent 3 → five-axis) per tier | ROI and efficiency axes vary with tier, not only accuracy |
| Tiers | `weak` = gpt-4o-mini, `mid` = gpt-5.4-mini, `strong` = gpt-5.4 | Spans the capability range |
| Repeats | **5 independent runs per tier** (distinct seeds) | Reliability measured across runs, matching Agent 2's 5-sample design |
| Matcher tier | **`strong`, fixed across all conditions** | The accuracy axis aligns reference↔units by an LLM matcher; holding it fixed prevents a better matcher from flattering a stronger pipeline. The matcher is an evaluation instrument, not part of the artifact under test. |
| Cache | **Disabled for pipeline calls** (`use_cache=False`) so repeats are truly independent; matcher MAY be cached since its inputs are identical across repeats of the same tier | Avoids collapsing 5 runs into 1 |
| Seeds | 42, 43, 44, 45, 46 | Reproducible |

## What is held constant

- The interview transcript (`data/raw/interview_tcb.txt`) and the partial expert
  reference (`data/raw/ground_truth_tcb.json`).
- All editable economic parameters (wage, capex, opex, automation ratios) from
  `run_manifest.json`. **Tier must not change the cost model** — otherwise ROI
  differences would confound model quality with assumption changes.
- Agent 2 sampling: 5 rollouts at temperature 0.7 *within* each run (this is the
  per-unit reliability signal); the 5 *runs* are a separate, outer repetition.

## Pre-run checklist (MUST do before executing)

1. **Strong-tier pricing — DONE.** All three tiers are priced in
   `run_manifest.json` (gpt-5.4 = $2.50 / $0.25 / $15.00 per 1M in / cached-in /
   out; gpt-5.4-mini = $0.75 / $0.075 / $4.50; gpt-4o-mini = $0.15 / $0.075 /
   $0.60), and `patch_notebooks.py` also writes these into notebook 00 so a
   run-from-00 will not reset them. No action unless prices change.
2. **Confirm gpt-5.4 API behavior**: whether it accepts `temperature=0.7`. If the
   model only supports a fixed temperature, Agent 2's 5-sample dispersion will
   collapse to ~0 and the reliability axis for that tier becomes degenerate. The
   existing `llm_call` already strips `temperature` on a `TypeError`, so the run
   will not crash — but note in the paper that strong-tier reliability reflects a
   fixed-temperature regime if that is the case. Verify and record.
3. **Set `.env`** with a valid `OPENAI_API_KEY` and the three `LLM_MODEL_*` names.
4. **Cost guard**: strong × 5 runs × full pipeline can be materially more
   expensive than the weak cache. Estimate before running (see cost note below).

## Execution

From the repo root, with `.env` populated:

```bash
python experiments/run_tier_sweep.py --tiers weak mid strong --repeats 5 \
    --matcher-tier strong --seeds 42 43 44 45 46
```

Outputs are written to `experiments/results/<tier>/run_<seed>/` (one five-axis
report per run) and aggregated into `experiments/results/tier_comparison.csv` and
`experiments/results/tier_comparison.json`.

## Metrics collected per run

- Accuracy: grade agreement, Cohen's κ, time MAE (min), time MAPE (%), matched
  pairs, recall gap.
- Reliability: mean/median CV (within-run Agent-2 dispersion).
- Efficiency: measured pipeline LLM cost (USD), annual saving (USD), ratio.
- Transparency: rationale coverage (%), grounded share (%).
- Robustness: clarifying-question rate (%), missing-field flags.

## Aggregation for the paper

For each tier report **mean ± standard deviation across the 5 runs** for every
metric. The headline table (accuracy κ and time MAPE by tier) goes in §5.1; the
full per-axis table goes in an appendix. If a monotonic improvement in κ / drop
in MAPE with tier appears, it directly answers "does a stronger model fix the
accuracy weakness?" — and if it does *not* improve, that is itself an important,
reportable finding (the limitation is the underdetermined interview, not the
model).

## Interpretation guardrails (keep in the paper)

- This remains a **single-interview, single-reference** demonstration. More tiers
  do not turn it into a confirmatory multi-process study; the paper's other
  limitations stand.
- The expert reference is authored by one analyst. Higher κ against it means
  closer agreement with that analyst, not ground-truth correctness.
- Because durations are absent from the interview, even the strong tier's time
  estimates are priors/inferences; MAPE is expected to stay high and should be
  read as such.

# Tier-Sweep Experiment — single unified notebook

The whole experiment now lives in ONE notebook, ONE code cell:

    notebooks/RUN_EXPERIMENT.ipynb

It contains the full pipeline (Agent 1 -> process graph -> Agent 2 -> Agent 3 ->
five-axis validation), the model-tier sweep, the repeated runs, and the
aggregation — all in a single self-contained cell whose top comment names it.
No %run, no nbconvert.exe, no external driver, no notebook-to-notebook patching.
This avoids every failure mode we hit earlier (AppLocker blocking nbconvert,
Windows path quoting in %run, and the cache/seed bug that made repeats identical).

## How the earlier std=0 bug is fixed here

The cache/seed controls are built directly into the merged llm_call, before the
cache lookup: when disable_cache is on, every call bypasses the cache, and the
active seed is mixed into the cache salt, so the five repeats are genuinely
independent (non-zero std). This was verified end-to-end offline.

## Run it

1. Put a `.env` at the repo root:
       OPENAI_API_KEY=sk-...
       LLM_MODEL_WEAK=gpt-4o-mini
       LLM_MODEL_MID=gpt-5.4-mini
       LLM_MODEL_STRONG=gpt-5.4
   (Pricing for all three tiers is already in artifacts/run_manifest.json.)

2. Launch Jupyter FROM THE REPO ROOT and open notebooks/RUN_EXPERIMENT.ipynb.

3. (Recommended smoke test) In the CONFIG dict at the top of the cell, set
       "smoke_test": True
   and Run All. This runs only the weak tier over 2 seeds. Confirm the printed
   "kappa std=" line is NON-zero for a varying metric (e.g. reliability CV or
   time MAPE) — that proves the repeats are independent. Then set smoke_test
   back to False.

4. Run All. It writes:
       experiments/results/tier_comparison.json   <-- send this back
       experiments/results/tier_comparison.csv
       experiments/results/<tier>/run_<seed>/five_axis_report.json

5. For paper tables, run notebooks/09_tier_sweep_aggregation.ipynb (unchanged).

## Config (top of the single cell)

    CONFIG = {
        "tiers": ["weak", "mid", "strong"],
        "seeds": [42, 43, 44, 45, 46],
        "matcher_tier": "strong",     # accuracy-axis matcher held fixed
        "disable_cache": True,        # REQUIRED for independent repeats
        "smoke_test": False,
    }

## Cost

With the cache genuinely off, all tiers x seeds make real API calls every run
(no free cache hits). Start with the smoke test, then scale to the full 3x5 run;
strong dominates the cost.

## Legacy files (optional, no longer required)

The earlier multi-notebook driver and patcher (run_tier_sweep.py,
patch_notebooks.py, notebooks 10) are left in place for reference but are NOT
needed — RUN_EXPERIMENT.ipynb supersedes them.
